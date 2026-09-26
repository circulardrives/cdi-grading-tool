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

"""Remote (multi-host) scanning: registry tokens, forwarding, fleet view."""

from __future__ import annotations

import json
import os
import socket
import stat
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from cdi_health.api import remote as remote_module
from cdi_health.api.remote import RemoteAddressError, forwarded_scan_body, parse_remote_address
from cdi_health.api.schemas import ScanRequest

REPO_ROOT = Path(__file__).resolve().parents[1]
MOCK_DATA_PATH = REPO_ROOT / "src" / "cdi_health" / "mock_data"
REMOTE_TOKEN = "remote-bench-secret"

REMOTE_SCAN = {
    "scanned_at": "2026-09-26T12:00:00+00:00",
    "grading_profile": "binary",
    "summary": {"total": 2, "healthy": 1, "warning": 0, "failed": 1, "ungraded": 0},
    "devices": [
        {"dut": "/dev/nvme0", "serial_number": "REMOTE-A", "health_grade": "PASS"},
        {"dut": "/dev/nvme1", "serial_number": "REMOTE-B", "health_grade": "FAIL"},
    ],
    # A newer remote reports its own view of these; they must be overridden.
    "machine_id": None,
    "executed_on": "local",
}


class FakeRemote:
    """Tiny cdi-health-api stand-in served from a background thread."""

    def __init__(self, token: str | None = REMOTE_TOKEN) -> None:
        self.token = token
        self.scan_status = 200
        self.scan_payload: Any = REMOTE_SCAN
        self.scan_delay = 0.0
        self.requests: list[dict[str, Any]] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: Any) -> None:
                return

            def _authorized(self) -> bool:
                return not fake.token or self.headers.get("X-API-Token") == fake.token

            def _send(self, status: int, payload: Any) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _record(self, body: Any = None) -> None:
                fake.requests.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "headers": {k.lower(): v for k, v in self.headers.items()},
                        "body": body,
                    }
                )

            def do_GET(self) -> None:  # noqa: N802
                self._record()
                if self.path.startswith("/api/v1/health"):
                    if fake.token and not self._authorized():
                        self._send(200, {"status": "ok", "version": "9.9.9"})
                    else:
                        self._send(
                            200,
                            {
                                "status": "ok",
                                "version": "9.9.9",
                                "is_root": True,
                                "api_token_enabled": bool(fake.token),
                            },
                        )
                elif self.path.startswith("/api/v1/jobs"):
                    if self._authorized():
                        self._send(200, [])
                    else:
                        self._send(401, {"detail": "Invalid API token"})
                else:
                    self._send(404, {"detail": "Not Found"})

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"null")
                self._record(body)
                if not self._authorized():
                    self._send(401, {"detail": "Invalid API token"})
                    return
                if fake.scan_delay:
                    time.sleep(fake.scan_delay)
                self._send(fake.scan_status, fake.scan_payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.address = f"127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> FakeRemote:
        self.thread.start()
        return self

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def scan_requests(self) -> list[dict[str, Any]]:
        return [r for r in self.requests if r["method"] == "POST"]


@pytest.fixture
def fake_remote() -> Iterator[FakeRemote]:
    remote = FakeRemote().start()
    yield remote
    remote.stop()


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CDI_HEALTH_API_ALLOW_NON_ROOT", "1")
    monkeypatch.setenv("CDI_HEALTH_API_MOCK_DATA", str(MOCK_DATA_PATH))
    monkeypatch.setenv("CDI_HEALTH_DATA_DIR", str(tmp_path / "api-data"))
    monkeypatch.delenv("CDI_HEALTH_API_TOKEN", raising=False)
    monkeypatch.delenv("CDI_HEALTH_API_BIND_HOST", raising=False)
    monkeypatch.delenv("CDI_HEALTH_API_NO_AUTH", raising=False)
    monkeypatch.delenv(remote_module.SCAN_TIMEOUT_ENV, raising=False)

    from cdi_health.api.app import create_app

    return TestClient(create_app())


def _closed_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _register(client: TestClient, name: str, address: str = "", token: str | None = REMOTE_TOKEN) -> dict:
    payload: dict[str, Any] = {"name": name, "hostname": name.lower(), "address": address}
    if token is not None:
        payload["api_token"] = token
    response = client.post("/api/v1/machines", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


# --- registry: write-only tokens ------------------------------------------


def test_api_token_is_write_only_and_never_returned(api_client: TestClient, tmp_path: Path) -> None:
    created = _register(api_client, "Bench A", "10.0.0.5:8844")
    assert created["has_api_token"] is True
    assert "api_token" not in created
    assert created["remote_version"] is None
    machine_id = created["id"]

    listed = api_client.get("/api/v1/machines").json()
    detail = api_client.get(f"/api/v1/machines/{machine_id}").json()
    assert listed[0]["has_api_token"] is True
    assert detail["has_api_token"] is True
    for body in (listed, detail):
        assert REMOTE_TOKEN not in json.dumps(body)
        assert "api_token" not in json.dumps(body).replace("has_api_token", "")

    # Omitted on PATCH = unchanged.
    patched = api_client.patch(f"/api/v1/machines/{machine_id}", json={"notes": "rack 2"}).json()
    assert patched["has_api_token"] is True
    assert REMOTE_TOKEN not in json.dumps(patched)

    # Replaced.
    patched = api_client.patch(f"/api/v1/machines/{machine_id}", json={"api_token": "rotated"}).json()
    assert patched["has_api_token"] is True
    assert api_client.app.state.runtime.machine_store.get_api_token(machine_id) == "rotated"

    # Empty string clears.
    cleared = api_client.patch(f"/api/v1/machines/{machine_id}", json={"api_token": ""}).json()
    assert cleared["has_api_token"] is False
    assert api_client.app.state.runtime.machine_store.get_api_token(machine_id) is None


def test_machines_store_persists_token_with_mode_600(api_client: TestClient, tmp_path: Path) -> None:
    created = _register(api_client, "Bench A", "10.0.0.5")
    store_path = tmp_path / "api-data" / "machines.json"
    assert stat.S_IMODE(store_path.stat().st_mode) == 0o600
    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert persisted["machines"][0]["api_token"] == REMOTE_TOKEN

    # Reloading the store keeps the token (and still hides it).
    from cdi_health.api.machines import MachineStore

    reloaded = MachineStore(tmp_path / "api-data")
    assert reloaded.get_api_token(created["id"]) == REMOTE_TOKEN
    assert "api_token" not in reloaded.get_machine(created["id"])


def test_machine_store_tightens_existing_file_mode(tmp_path: Path) -> None:
    from cdi_health.api.machines import MachineStore

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    store_path = data_dir / "machines.json"
    store_path.write_text('{"machines": [], "latest_scans": {}}', encoding="utf-8")
    os.chmod(store_path, 0o644)
    MachineStore(data_dir)
    assert stat.S_IMODE(store_path.stat().st_mode) == 0o600


def test_machine_status_accepts_auth_failed(api_client: TestClient) -> None:
    machine_id = _register(api_client, "Bench A", token=None)["id"]
    response = api_client.patch(f"/api/v1/machines/{machine_id}", json={"status": "auth_failed"})
    assert response.status_code == 200
    assert response.json()["status"] == "auth_failed"


# --- address parsing / SSRF guard ------------------------------------------


def test_parse_remote_address_defaults_and_rejections() -> None:
    assert parse_remote_address("192.168.1.20") == ("http", "192.168.1.20", 8844)
    assert parse_remote_address("192.168.1.20:9000") == ("http", "192.168.1.20", 9000)
    assert parse_remote_address("http://bench-01.lan:8844/") == ("http", "bench-01.lan", 8844)
    for bad in ("", "https://10.0.0.5", "[fe80::1]:8844", "user@10.0.0.5", "10.0.0.5:notaport"):
        with pytest.raises(RemoteAddressError):
            parse_remote_address(bad)


def test_forwarded_scan_body_strips_local_fields() -> None:
    body = forwarded_scan_body(
        ScanRequest(
            machine_id="m1",
            mock_data="/tmp/x",
            mock_file="/tmp/y.json",
            config="/etc/cdi-health/t.yaml",
            grading_profile="abcdf",
            ignore_ata=True,
            device="/dev/nvme0",
        )
    )
    assert body == {
        "ignore_ata": True,
        "ignore_nvme": False,
        "ignore_scsi": False,
        "device": "/dev/nvme0",
        "grading_profile": "abcdf",
    }


def test_remote_scan_rejects_public_address(api_client: TestClient) -> None:
    machine_id = _register(api_client, "Public", "8.8.8.8:8844")["id"]
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 400
    assert response.json()["detail"] == "Remote host address must be on a private network"

    check = api_client.post(f"/api/v1/machines/{machine_id}/check")
    assert check.status_code == 400


def test_remote_scan_rejects_hostname_resolving_public(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_getaddrinfo(host: str, port: int, *_args: Any, **_kwargs: Any) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(remote_module.socket, "getaddrinfo", fake_getaddrinfo)
    machine_id = _register(api_client, "Sneaky", "bench.example.com")["id"]
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 400


# --- scan forwarding --------------------------------------------------------


def test_remote_scan_forwards_body_and_token_and_persists(api_client: TestClient, fake_remote: FakeRemote) -> None:
    machine_id = _register(api_client, "Bench A", fake_remote.address)["id"]
    runtime = api_client.app.state.runtime

    # The local hardware lock is not needed for a remote scan.
    assert runtime.hardware_lock.acquire(blocking=False)
    try:
        response = api_client.post(
            "/api/v1/scan",
            json={
                "machine_id": machine_id,
                "mock_data": str(MOCK_DATA_PATH),
                "config": "/etc/cdi-health/thresholds.yaml",
                "grading_profile": "abcdf",
                "ignore_scsi": True,
            },
        )
    finally:
        runtime.hardware_lock.release()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["executed_on"] == "remote"
    assert body["machine_id"] == machine_id
    assert body["remote_address"] == fake_remote.address
    assert [d["serial_number"] for d in body["devices"]] == ["REMOTE-A", "REMOTE-B"]

    [forwarded] = fake_remote.scan_requests()
    assert forwarded["path"] == "/api/v1/scan"
    assert forwarded["headers"]["x-api-token"] == REMOTE_TOKEN
    assert forwarded["body"] == {
        "ignore_ata": False,
        "ignore_nvme": False,
        "ignore_scsi": True,
        "grading_profile": "abcdf",
    }

    machine = api_client.get(f"/api/v1/machines/{machine_id}").json()
    assert machine["status"] == "reachable"
    assert machine["last_scan_status"] == "success"
    assert machine["last_scan_summary"]["failed"] == 1

    history = api_client.get(f"/api/v1/history?machine_id={machine_id}").json()
    assert len(history) == 1
    assert history[0]["device_count"] == 2
    assert history[0]["mock"] is False

    cached = api_client.get(f"/api/v1/devices?machine_id={machine_id}").json()
    assert cached["executed_on"] == "remote"
    assert cached["scanned_at"] == body["scanned_at"]

    # Remote results do not become this API's own latest scan.
    assert runtime.latest_scan is None


def test_devices_refresh_on_remote_machine_forwards(api_client: TestClient, fake_remote: FakeRemote) -> None:
    machine_id = _register(api_client, "Bench A", fake_remote.address)["id"]
    response = api_client.get(f"/api/v1/devices?machine_id={machine_id}&refresh=true")
    assert response.status_code == 200
    assert response.json()["executed_on"] == "remote"
    assert len(fake_remote.scan_requests()) == 1


def test_local_scan_reports_executed_on_local(api_client: TestClient) -> None:
    machine_id = _register(api_client, "Local bench", token=None)["id"]
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 200
    body = response.json()
    assert body["executed_on"] == "local"
    assert body["machine_id"] == machine_id
    assert body["remote_address"] is None


def test_remote_scan_bad_token_maps_to_502_auth_failed(api_client: TestClient, fake_remote: FakeRemote) -> None:
    machine_id = _register(api_client, "Bench A", fake_remote.address, token="wrong")["id"]
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 502
    assert response.json()["detail"] == "Host 'Bench A' rejected the API token"
    assert api_client.get(f"/api/v1/machines/{machine_id}").json()["status"] == "auth_failed"


def test_remote_scan_unreachable_maps_to_502(api_client: TestClient) -> None:
    address = f"127.0.0.1:{_closed_port()}"
    machine_id = _register(api_client, "Bench Down", address)["id"]
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 502
    assert response.json()["detail"] == f"Host 'Bench Down' is unreachable at {address}"
    assert api_client.get(f"/api/v1/machines/{machine_id}").json()["status"] == "unreachable"


def test_remote_scan_timeout_maps_to_504(
    api_client: TestClient,
    fake_remote: FakeRemote,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(remote_module.SCAN_TIMEOUT_ENV, "0.3")
    fake_remote.scan_delay = 1.5
    machine_id = _register(api_client, "Bench Slow", fake_remote.address)["id"]
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 504
    assert response.json()["detail"] == "Host 'Bench Slow' timed out"
    assert api_client.get(f"/api/v1/machines/{machine_id}").json()["status"] == "unreachable"


def test_remote_scan_409_passthrough(api_client: TestClient, fake_remote: FakeRemote) -> None:
    fake_remote.scan_status = 409
    fake_remote.scan_payload = {"detail": "Drive hardware is busy with another scan."}
    machine_id = _register(api_client, "Bench A", fake_remote.address)["id"]
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 409
    assert response.json()["detail"] == "Drive hardware is busy with another scan."
    assert api_client.get(f"/api/v1/machines/{machine_id}").json()["status"] == "reachable"


def test_remote_scan_other_4xx_and_5xx(api_client: TestClient, fake_remote: FakeRemote) -> None:
    machine_id = _register(api_client, "Bench A", fake_remote.address)["id"]

    fake_remote.scan_status = 422
    fake_remote.scan_payload = {"detail": [{"msg": "bad device\n" + "x" * 500}]}
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail.startswith("bad device")
    assert "\n" not in detail
    assert len(detail) <= 200

    fake_remote.scan_status = 500
    fake_remote.scan_payload = {"detail": "Traceback: /secret/path"}
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 502
    assert response.json()["detail"] == "Host 'Bench A' scan failed"

    fake_remote.scan_status = 200
    fake_remote.scan_payload = {"not": "a scan"}
    response = api_client.post("/api/v1/scan", json={"machine_id": machine_id})
    assert response.status_code == 502
    assert api_client.get(f"/api/v1/history?machine_id={machine_id}").json() == []


# --- /machines/{id}/check ---------------------------------------------------


def test_check_reachable_sets_remote_version(api_client: TestClient, fake_remote: FakeRemote) -> None:
    machine_id = _register(api_client, "Bench A", fake_remote.address)["id"]
    response = api_client.post(f"/api/v1/machines/{machine_id}/check")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["health"]["is_root"] is True
    assert body["machine"]["status"] == "reachable"
    assert body["machine"]["remote_version"] == "9.9.9"
    assert body["machine"]["last_seen_at"] is not None
    assert "api_token" not in body["machine"]
    assert all(r["headers"].get("x-api-token") == REMOTE_TOKEN for r in fake_remote.requests)


def test_check_auth_failed_with_wrong_or_missing_token(api_client: TestClient, fake_remote: FakeRemote) -> None:
    for token in ("wrong", None):
        machine_id = _register(api_client, f"Bench {token}", fake_remote.address, token=token)["id"]
        body = api_client.post(f"/api/v1/machines/{machine_id}/check").json()
        assert body["machine"]["status"] == "auth_failed"
        assert body["error"] == f"Host 'Bench {token}' rejected the API token"
        assert body["health"] == {"status": "ok", "version": "9.9.9"}


def test_check_unreachable_and_no_address(api_client: TestClient) -> None:
    address = f"127.0.0.1:{_closed_port()}"
    machine_id = _register(api_client, "Bench Down", address)["id"]
    body = api_client.post(f"/api/v1/machines/{machine_id}/check").json()
    assert body["machine"]["status"] == "unreachable"
    assert body["health"] is None
    assert body["error"] == f"Host 'Bench Down' is unreachable at {address}"

    local_id = _register(api_client, "No address", token=None)["id"]
    assert api_client.post(f"/api/v1/machines/{local_id}/check").status_code == 400
    assert api_client.post("/api/v1/machines/missing/check").status_code == 404


# --- /fleet/devices ---------------------------------------------------------


def test_fleet_devices_aggregates_hosts_with_one_failing(api_client: TestClient, fake_remote: FakeRemote) -> None:
    local = api_client.post("/api/v1/scan", json={})
    assert local.status_code == 200
    local_body = local.json()

    good_id = _register(api_client, "Bench Good", fake_remote.address)["id"]
    down_address = f"127.0.0.1:{_closed_port()}"
    down_id = _register(api_client, "Bench Down", down_address)["id"]
    _register(api_client, "No address", token=None)  # registry-only: not in the fleet view

    response = api_client.get("/api/v1/fleet/devices?refresh=true")
    assert response.status_code == 200, response.text
    body = response.json()

    hosts = {host["name"]: host for host in body["hosts"]}
    assert set(hosts) == {"Local API", "Bench Good", "Bench Down"}
    assert body["hosts"][0]["name"] == "Local API"

    assert hosts["Local API"]["machine_id"] is None
    assert hosts["Local API"]["executed_on"] == "local"
    assert hosts["Local API"]["device_count"] == local_body["summary"]["total"]

    assert hosts["Bench Good"]["machine_id"] == good_id
    assert hosts["Bench Good"]["status"] == "reachable"
    assert hosts["Bench Good"]["error"] is None
    assert hosts["Bench Good"]["device_count"] == 2
    assert hosts["Bench Good"]["executed_on"] == "remote"

    assert hosts["Bench Down"]["machine_id"] == down_id
    assert hosts["Bench Down"]["status"] == "unreachable"
    assert hosts["Bench Down"]["error"] == f"Host 'Bench Down' is unreachable at {down_address}"
    assert hosts["Bench Down"]["device_count"] == 0
    assert hosts["Bench Down"]["summary"] is None

    remote_devices = [d for d in body["devices"] if d["machine_id"] == good_id]
    assert {d["serial_number"] for d in remote_devices} == {"REMOTE-A", "REMOTE-B"}
    assert all(d["machine_name"] == "Bench Good" for d in remote_devices)
    assert all(d["host_address"] == fake_remote.address for d in remote_devices)
    local_devices = [d for d in body["devices"] if d["machine_id"] is None]
    assert all(d["machine_name"] == "Local API" and d["host_address"] is None for d in local_devices)

    assert body["summary"]["total"] == local_body["summary"]["total"] + 2
    assert body["summary"]["failed"] == local_body["summary"]["failed"] + 1
    assert len(body["devices"]) == body["summary"]["total"]
    assert body["generated_at"]

    # Without refresh: cached results only, no new remote scans, no errors.
    scans_before = len(fake_remote.scan_requests())
    cached = api_client.get("/api/v1/fleet/devices").json()
    assert len(fake_remote.scan_requests()) == scans_before
    assert all(host["error"] is None for host in cached["hosts"])
    assert cached["summary"] == body["summary"]


def test_fleet_devices_empty_without_scans(api_client: TestClient) -> None:
    body = api_client.get("/api/v1/fleet/devices").json()
    assert body["hosts"] == []
    assert body["devices"] == []
    assert body["summary"] == {"total": 0, "healthy": 0, "warning": 0, "failed": 0, "ungraded": 0}
