#
# Copyright (c) 2026 Circular Drive Initiative.
#
# This file is part of CDI Health.
# See https://github.com/circulardrives/cdi-grading-tool/ for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Minimal stdlib HTTP client for forwarding calls to a remote cdi-health-api.

A registered machine with an ``address`` is a grading bench running its own
``cdi-health-api`` (default port 8844) with its own ``X-API-Token``. This
module turns that address into a validated endpoint and performs blocking
requests against it; callers run it from FastAPI's sync (threadpool) routes.

Security:

* Only private / link-local / loopback IPv4 targets are allowed (the same
  ranges LAN discovery may probe). Hostnames are resolved once and every
  resolved address must be private; the request is then sent to the
  validated IP (with the original ``Host`` header) so DNS rebinding cannot
  redirect it.
* Redirects are never followed and environment proxies are ignored, so the
  host token is only ever sent to the validated address.
* Only ``http://`` is implemented today. ``RemoteEndpoint.scheme`` and
  ``SUPPORTED_SCHEMES`` are the extension points for TLS.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from cdi_health.api.discovery import DEFAULT_CDI_PORT, is_private_ipv4

HEALTH_TIMEOUT_SECONDS = 5.0
# Self-test start/abort/status and job polling: starting a test returns quickly
# (the job itself runs on the remote), so these never wait for completion.
REMOTE_CALL_TIMEOUT_SECONDS = 30.0
DEFAULT_SCAN_TIMEOUT_SECONDS = 300.0
SCAN_TIMEOUT_ENV = "CDI_HEALTH_REMOTE_SCAN_TIMEOUT"
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
MAX_DETAIL_CHARS = 200
SUPPORTED_SCHEMES = ("http",)
PRIVATE_NETWORK_DETAIL = "Remote host address must be on a private network"

# ScanRequest fields never forwarded: local registry ids and local file paths.
SCAN_FIELDS_NOT_FORWARDED = frozenset({"machine_id", "mock_data", "mock_file", "config"})

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]+")


class RemoteHostError(Exception):
    """A forwarded call failed; carries the HTTP mapping and new machine status."""

    def __init__(self, status_code: int, detail: str, machine_status: str | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.machine_status = machine_status


class RemoteAddressError(RemoteHostError):
    """The configured address is invalid or not on a private network (HTTP 400)."""

    def __init__(self, detail: str = PRIVATE_NETWORK_DETAIL) -> None:
        super().__init__(400, detail, None)


@dataclass(frozen=True)
class RemoteEndpoint:
    """A validated remote API endpoint."""

    scheme: str
    host: str
    port: int
    ip: str

    @property
    def host_header(self) -> str:
        return f"{self.host}:{self.port}"

    def url(self, path: str) -> str:
        return f"{self.scheme}://{self.ip}:{self.port}{path}"


def remote_scan_timeout() -> float:
    """Scan forwarding timeout in seconds (env ``CDI_HEALTH_REMOTE_SCAN_TIMEOUT``)."""
    raw = os.getenv(SCAN_TIMEOUT_ENV)
    if not raw:
        return DEFAULT_SCAN_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_SCAN_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_SCAN_TIMEOUT_SECONDS


def parse_remote_address(address: str) -> tuple[str, str, int]:
    """Split ``ip``, ``host:port`` or ``http://host:port`` into ``(scheme, host, port)``."""
    cleaned = (address or "").strip()
    if not cleaned:
        raise RemoteAddressError("Machine has no remote address")

    scheme = "http"
    if "://" in cleaned:
        scheme, _, cleaned = cleaned.partition("://")
        scheme = scheme.lower()
        if scheme not in SUPPORTED_SCHEMES:
            raise RemoteAddressError("Only http:// remote host addresses are supported")
    # Drop any path/query; only scheme://host[:port] is meaningful.
    cleaned = cleaned.split("/", 1)[0].split("?", 1)[0]
    if "@" in cleaned or cleaned.startswith("["):
        # userinfo or IPv6 literals are not supported.
        raise RemoteAddressError()

    host, port = cleaned, DEFAULT_CDI_PORT
    if cleaned.count(":") == 1:
        host, _, port_text = cleaned.partition(":")
        try:
            port = int(port_text)
        except ValueError as exc:
            raise RemoteAddressError("Invalid remote host port") from exc
    elif ":" in cleaned:
        raise RemoteAddressError()

    host = host.strip()
    if not host or not 1 <= port <= 65535:
        raise RemoteAddressError("Invalid remote host address")
    return scheme, host, port


def resolve_endpoint(address: str, *, name: str) -> RemoteEndpoint:
    """Validate an address and pin it to a private IPv4 address.

    Raises :class:`RemoteAddressError` (400) for public/invalid targets and
    :class:`RemoteHostError` (502, unreachable) when a hostname cannot be resolved.
    """
    scheme, host, port = parse_remote_address(address)
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, OSError) as exc:
        raise RemoteHostError(502, f"Host '{name}' is unreachable at {address}", "unreachable") from exc

    ips = [info[4][0] for info in infos]
    if not ips or not all(is_private_ipv4(ip) for ip in ips):
        raise RemoteAddressError()
    return RemoteEndpoint(scheme=scheme, host=host, port=port, ip=ips[0])


def sanitize_detail(detail: Any) -> str | None:
    """Reduce a remote error ``detail`` to a short single-line string."""
    if detail is None:
        return None
    if isinstance(detail, list):
        parts = [str(item.get("msg", item)) if isinstance(item, dict) else str(item) for item in detail]
        text = "; ".join(parts)
    elif isinstance(detail, str):
        text = detail
    else:
        text = json.dumps(detail, default=str)
    text = _CONTROL_CHARS.sub(" ", text).strip()
    if not text:
        return None
    return text[:MAX_DETAIL_CHARS]


def remote_auth_mode(health: dict[str, Any] | None) -> str | None:
    """Return a remote host's auth mode (``"none"`` / ``"token"``) from its /health payload.

    Newer APIs report ``auth_mode`` directly. Older ones are inferred: the
    full payload carries ``api_token_enabled``; the minimal ``{status,
    version}`` payload is only served when a token is enforced.
    """
    if not isinstance(health, dict):
        return None
    mode = health.get("auth_mode")
    if mode in ("none", "token"):
        return mode
    if "api_token_enabled" in health:
        return "token" if health.get("api_token_enabled") else "none"
    return "token" if health.get("status") == "ok" else None


def forwarded_scan_body(request: Any) -> dict[str, Any]:
    """ScanRequest -> JSON body for the remote host (no ids or local paths)."""
    payload = request.model_dump(mode="json", exclude_none=True)
    return {key: value for key, value in payload.items() if key not in SCAN_FIELDS_NOT_FORWARDED}


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so the host token never leaves the validated address."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


def _build_opener() -> urllib.request.OpenerDirector:
    # ProxyHandler({}) ignores HTTP(S)_PROXY: LAN benches are reached directly.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirectHandler())


class RemoteHostClient:
    """Blocking client for one registered remote cdi-health-api host."""

    def __init__(
        self,
        *,
        name: str,
        address: str,
        token: str | None,
        health_timeout: float = HEALTH_TIMEOUT_SECONDS,
        scan_timeout: float | None = None,
    ) -> None:
        self.name = name
        self.address = address
        self.token = token or None
        self.health_timeout = health_timeout
        self.scan_timeout = scan_timeout if scan_timeout is not None else remote_scan_timeout()
        self.endpoint = resolve_endpoint(address, name=name)
        self._opener = _build_opener()

    # -- transport -----------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        timeout: float,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        headers = {
            "Accept": "application/json",
            "Host": self.endpoint.host_header,
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        # No stored token (e.g. a --no-auth lab bench): send no header at all.
        if self.token:
            headers["X-API-Token"] = self.token
        request = urllib.request.Request(self.endpoint.url(path), data=data, method=method, headers=headers)

        try:
            with self._opener.open(request, timeout=timeout) as response:
                status = response.status
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            status = exc.code
            try:
                raw = exc.read(MAX_RESPONSE_BYTES + 1)
            except (OSError, http.client.HTTPException):
                raw = b""
            finally:
                exc.close()
        except TimeoutError as exc:
            raise self._timeout_error() from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise self._timeout_error() from exc
            raise self._unreachable_error() from exc
        except (http.client.HTTPException, OSError) as exc:
            raise self._unreachable_error() from exc

        if len(raw) > MAX_RESPONSE_BYTES:
            raise RemoteHostError(502, f"Host '{self.name}' returned an oversized response", "reachable")
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None
        return status, payload

    def _timeout_error(self) -> RemoteHostError:
        return RemoteHostError(504, f"Host '{self.name}' timed out", "unreachable")

    def _unreachable_error(self) -> RemoteHostError:
        return RemoteHostError(502, f"Host '{self.name}' is unreachable at {self.address}", "unreachable")

    def _raise_for_status(self, status: int, payload: Any, *, failure: str) -> None:
        if 200 <= status < 300:
            return
        remote_detail = sanitize_detail(payload.get("detail")) if isinstance(payload, dict) else None
        if status in (401, 403):
            raise RemoteHostError(502, f"Host '{self.name}' rejected the API token", "auth_failed")
        if status == 409:
            raise RemoteHostError(409, remote_detail or f"Host '{self.name}' is busy", "reachable")
        if 400 <= status < 500:
            raise RemoteHostError(status, remote_detail or f"Host '{self.name}' rejected the request", "reachable")
        raise RemoteHostError(502, failure, "reachable")

    # -- operations ----------------------------------------------------

    def health(self) -> dict[str, Any]:
        """GET /api/v1/health (token attached). Raises when the host is not a CDI API."""
        status, payload = self._request("GET", "/api/v1/health", timeout=self.health_timeout)
        self._raise_for_status(status, payload, failure=f"Host '{self.name}' health check failed")
        if not isinstance(payload, dict) or payload.get("status") != "ok":
            raise RemoteHostError(
                502,
                f"Host '{self.name}' at {self.address} did not respond like a CDI Health API",
                "unreachable",
            )
        return payload

    def verify_token(self) -> None:
        """Probe an authenticated endpoint; 401/403 raises an ``auth_failed`` error.

        ``/health`` never returns 401 (unauthenticated callers just get a
        minimal payload, and loopback callers always get the full one), so an
        authenticated route is the only reliable signal. ``GET /api/v1/jobs``
        is used because it is cheap (in-memory) and exists on every version.
        """
        status, payload = self._request("GET", "/api/v1/jobs?limit=1", timeout=self.health_timeout)
        if status in (401, 403):
            self._raise_for_status(status, payload, failure="")

    def scan(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /api/v1/scan on the remote host and return its ScanResponse JSON."""
        status, payload = self._request("POST", "/api/v1/scan", timeout=self.scan_timeout, body=body)
        self._raise_for_status(status, payload, failure=f"Host '{self.name}' scan failed")
        if not isinstance(payload, dict) or not isinstance(payload.get("devices"), list):
            raise RemoteHostError(502, f"Host '{self.name}' returned an invalid scan response", "reachable")
        return payload

    def call(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        timeout: float = REMOTE_CALL_TIMEOUT_SECONDS,
    ) -> Any:
        """Forward one JSON API call to the remote host and return its decoded payload.

        ``path`` must be a fixed API path (callers quote any path parameters);
        ``query`` values of ``None`` are dropped. Errors map like :meth:`scan`.
        """
        if query:
            params = {key: value for key, value in query.items() if value is not None}
            if params:
                path = f"{path}?{urllib.parse.urlencode(params)}"
        status, payload = self._request(method, path, timeout=timeout, body=body)
        self._raise_for_status(status, payload, failure=f"Host '{self.name}' request failed")
        if payload is None:
            raise RemoteHostError(502, f"Host '{self.name}' returned an invalid response", "reachable")
        return payload
