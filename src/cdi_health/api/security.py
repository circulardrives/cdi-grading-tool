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

from __future__ import annotations

import ipaddress
import os
import socket

from fastapi import Header, HTTPException, Request, status

ALLOW_NON_ROOT_ENV = "CDI_HEALTH_API_ALLOW_NON_ROOT"
API_TOKEN_ENV = "CDI_HEALTH_API_TOKEN"
BIND_HOST_ENV = "CDI_HEALTH_API_BIND_HOST"


def is_root_user() -> bool:
    """Return True if the current process is running as root."""
    return hasattr(os, "geteuid") and os.geteuid() == 0


def allow_non_root_mode() -> bool:
    """Allow non-root mode for local development/testing."""
    return os.getenv(ALLOW_NON_ROOT_ENV, "0") == "1"


def assert_root_access() -> None:
    """
    Ensure the backend process has root privileges.

    Real device operations rely on privileged access to block devices.
    """
    if is_root_user() or allow_non_root_mode():
        return

    raise PermissionError(
        "CDI Health API must run as root for real device operations. "
        f"Set {ALLOW_NON_ROOT_ENV}=1 for non-root development mode."
    )


def api_token_is_enabled() -> bool:
    """Return True when an API token is configured."""
    return bool(os.getenv(API_TOKEN_ENV))


def get_configured_api_token() -> str | None:
    """Return the configured API token, or None when unset."""
    token = os.getenv(API_TOKEN_ENV)
    return token if token else None


def is_loopback_host(host: str) -> bool:
    """Return True when *host* resolves only to loopback addresses."""
    normalized = (host or "").strip().lower()
    if not normalized:
        return False
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return True

    # Strip IPv6 brackets if present.
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]

    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(normalized, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    if not infos:
        return False

    for info in infos:
        try:
            if not ipaddress.ip_address(info[4][0]).is_loopback:
                return False
        except (ValueError, IndexError):
            return False
    return True


def assert_token_required_for_bind(host: str) -> None:
    """
    Fail fast when binding a non-loopback interface without an API token.

    Non-loopback binds (0.0.0.0, LAN IPs, hostnames) expose drive-control
    endpoints on the network and must require authentication.
    """
    if is_loopback_host(host):
        return
    if api_token_is_enabled():
        return
    raise RuntimeError(
        f"CDI Health API refuses to bind non-loopback host {host!r} without "
        f"{API_TOKEN_ENV}. Set a strong token or bind to 127.0.0.1."
    )


def verify_api_token(x_api_token: str | None = Header(default=None, alias="X-API-Token")) -> None:
    """
    Header-based API token check for dashboard/backend traffic.

    When no token is configured (loopback-only deployments), this is a no-op.
    """
    expected = get_configured_api_token()
    if not expected:
        return

    if x_api_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )


def optional_api_token(
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
) -> bool:
    """
    Return True when the request presents a valid API token.

    Does not raise when the token is missing; used by /health to decide
    whether to return the full diagnostic payload.
    """
    expected = get_configured_api_token()
    if not expected:
        return True
    return x_api_token == expected


def client_is_loopback(request: Request) -> bool:
    """Return True when the HTTP client appears to be on loopback."""
    client = request.client
    if client is None:
        return False
    try:
        return ipaddress.ip_address(client.host).is_loopback
    except ValueError:
        return False
