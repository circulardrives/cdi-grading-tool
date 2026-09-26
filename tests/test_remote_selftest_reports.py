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

"""Reports from saved scans (fleet / history) and self-tests forwarded to remote benches."""

from __future__ import annotations

import csv
import io
import json
import os
import socket
import stat
import threading
from collections.abc import Iterator
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from cdi_health.api import remote as remote_module
from cdi_health.api import services

REPO_ROOT = Path(__file__).resolve().parents[1]
MOCK_DATA_PATH = REPO_ROOT / "src" / "cdi_health" / "mock_data"
MOCK_NVME_FILE = MOCK_DATA_PATH / "nvme" / "SSDPE2KE032T8_healthy.json"
REMOTE_TOKEN = "remote-bench-secret"

REMOTE_JOB = {
    "job_id": "remote-job-1",
    "job_type": "selftest",
    "status": "queued",
    "payload": {"device": "/dev/nvme0", "test_type": "extended"},
    "created_at": "2026-09-26T12:00:00+00:00",
    "updated_at": "2026-09-26T12:00:00+00:00",
}
REMOTE_STATUS = {
    "devices": [{"device": "/dev/nvme0", "supported": True, "status": "in_progress", "in_progress": True}],
    "total": 1,
}


class FakeBench:
    """cdi-health-api stand-in answering the self-test / job routes."""

    def __init__(self, token: str | None = REMOTE_TOKEN) -> None:
        self.token = token
        self.requests: list[dict[str, Any]] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: Any) -> None:
                return

            def _send(self, status: int, payload: Any) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _handle(self, body: Any = None) -> None:
                fake.requests.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "headers": {k.lower(): v for k, v in self.headers.items()},
                        "body": body,
                    }
                )
                if fake.token and self.headers.get("X-API-Token") != fake.token:
                    self._send(401, {"detail": "Invalid API token"})
                    return
                route = (self.command, self.path.split("?", 1)[0])
                if route == ("POST", "/api/v1/selftests"):
                    self._send(200, REMOTE_JOB)
                elif route == ("POST", "/api/v1/selftests/abort"):
                    self._send(200, {"device": body.get("device"), "aborted": True})
                elif route == ("GET", "/api/v1/selftests/status"):
                    self._send(200, REMOTE_STATUS)
                elif route == ("GET", "/api/v1/jobs"):
                    self._send(200, [REMOTE_JOB])
                elif route == ("GET", "/api/v1/jobs/remote-job-1"):
                    self._send(200, {**REMOTE_JOB, "status": "running"})
                elif route[1].startswith("/api/v1/jobs/"):
                    self._send(404, {"detail": "Job not found"})
                else:
                    self._send(404, {"detail": "Not Found"})

            def do_GET(self) -> None:  # noqa: N802
                self._handle()

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                self._handle(json.loads(self.rfile.read(length) or b"null"))

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.address = f"127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def last(self) -> dict[str, Any]:
        return self.requests[-1]


@pytest.fixture
def bench() -> Iterator[FakeBench]:
    fake = FakeBench()
    yield fake
    fake.stop()


@pytest.fixture
def api_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "api-data"
    monkeypatch.setenv("CDI_HEALTH_API_ALLOW_NON_ROOT", "1")
    monkeypatch.setenv("CDI_HEALTH_API_MOCK_DATA", str(MOCK_DATA_PATH))
    monkeypatch.setenv("CDI_HEALTH_DATA_DIR", str(data_dir))
    monkeypatch.delenv("CDI_HEALTH_API_TOKEN", raising=False)
    monkeypatch.delenv("CDI_HEALTH_API_BIND_HOST", raising=False)
    monkeypatch.delenv("CDI_HEALTH_API_NO_AUTH", raising=False)
    monkeypatch.delenv(remote_module.SCAN_TIMEOUT_ENV, raising=False)
    return data_dir


@pytest.fixture
def api_client(api_env: Path) -> TestClient:
    from cdi_health.api.app import create_app

    return TestClient(create_app())


def _register(client: TestClient, name: str, address: str = "", token: str | None = REMOTE_TOKEN) -> dict:
    payload: dict[str, Any] = {"name": name, "hostname": name.lower(), "address": address}
    if token is not None:
        payload["api_token"] = token
    response = client.post("/api/v1/machines", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _closed_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _forbid_local_scans(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("saved-scan reports must not scan drives")

    monkeypatch.setattr(services, "_collect_devices", _boom)
    monkeypatch.setattr(services, "run_scan", _boom)
    monkeypatch.setattr(services, "generate_report", _boom)
    import cdi_health.api.app as app_module

    monkeypatch.setattr(app_module, "run_scan", _boom)
    monkeypatch.setattr(app_module, "generate_report", _boom)


def _graded_device_with_recorded_grade(grade: str, score: int) -> tuple[dict[str, Any], str]:
    """A scored mock device whose stored grade differs from what re-scoring gives."""
    scan = services.run_scan(services.ScanRequest(mock_file=str(MOCK_NVME_FILE)))
    device = dict(scan["devices"][0])
    rescored_grade = str(device.get("final_grade") or device.get("health_grade"))
    assert rescored_grade != grade
    device.update(health_grade=grade, final_grade=grade, health_score=score, health_status="Warning")
    return device, rescored_grade


def _store_remote_scan(client: TestClient, machine_id: str, devices: list[dict], scanned_at: str) -> None:
    runtime = client.app.state.runtime
    result = {
        "scanned_at": scanned_at,
        "grading_profile": "abcdf",
        "summary": {"total": len(devices), "healthy": 0, "warning": len(devices), "failed": 0, "ungraded": 0},
        "devices": devices,
        "machine_id": machine_id,
        "executed_on": "remote",
    }
    assert runtime.machine_store.record_scan(machine_id, result) is not None
    runtime.history_store.record_scan(result, machine_id=machine_id)


def _csv_rows(client: TestClient, filename: str) -> list[dict[str, str]]:
    response = client.get(f"/api/v1/reports/{filename}")
    assert response.status_code == 200
    return list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))


# --- reports from saved scans ----------------------------------------------


def test_fleet_report_uses_stored_scans_and_preserves_grades(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    device, rescored_grade = _graded_device_with_recorded_grade("D", 42)
    bench_01 = _register(api_client, "bench-01", "10.0.0.9:8844")
    bench_02 = _register(api_client, "bench-02", "10.0.0.10:8844")
    _store_remote_scan(api_client, bench_01["id"], [device], "2026-09-26T08:59:00+00:00")
    _store_remote_scan(
        api_client,
        bench_02["id"],
        [{**device, "serial_number": "OTHER-SERIAL"}],
        "2026-09-26T09:30:00+00:00",
    )
    _forbid_local_scans(monkeypatch)
    # Held hardware lock: saved-scan reports must not need it.
    runtime = api_client.app.state.runtime
    assert runtime.hardware_lock.acquire(blocking=False)
    try:
        response = api_client.post("/api/v1/reports", json={"source": "fleet", "format": "csv"})
    finally:
        runtime.hardware_lock.release()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "fleet"
    assert body["devices_count"] == 2
    assert {h["name"] for h in body["hosts"]} == {"bench-01", "bench-02"}
    assert all(h["device_count"] == 1 for h in body["hosts"])

    rows = _csv_rows(api_client, body["filename"])
    assert {row["Host"] for row in rows} == {"bench-01", "bench-02"}
    assert all(row["Grade"] == "D" and row["Health score"] == "42" for row in rows)
    assert rescored_grade not in {row["Grade"] for row in rows}
    assert {row["Scanned at"] for row in rows} == {"2026-09-26 08:59 UTC", "2026-09-26 09:30 UTC"}
    header = list(rows[0].keys())
    assert header.index("Host") == header.index("Serial") + 1


def test_fleet_html_report_has_host_columns_and_source_line(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    device, rescored_grade = _graded_device_with_recorded_grade("B", 80)
    bench_01 = _register(api_client, "bench-01", "10.0.0.9:8844")
    _store_remote_scan(api_client, bench_01["id"], [device], "2026-09-26T08:59:00+00:00")
    _forbid_local_scans(monkeypatch)

    response = api_client.post("/api/v1/reports", json={"source": "fleet", "format": "html"})
    assert response.status_code == 200, response.text
    html = api_client.get(f"/api/v1/reports/{response.json()['filename']}").text
    assert "Source: Saved scans — bench-01 (2026-09-26 08:59 UTC)" in html
    assert "<th>Host</th><th>Scanned at</th>" in html
    assert 'title="Host"' in html  # advanced table header
    assert "Grade B" in html
    assert f"Grade {rescored_grade}" not in html


def test_history_report_with_ids(api_client: TestClient) -> None:
    scanned = api_client.post("/api/v1/scan", json={"mock_file": str(MOCK_NVME_FILE)})
    assert scanned.status_code == 200, scanned.text
    recorded_grade = scanned.json()["devices"][0]["health_grade"]
    history_id = api_client.get("/api/v1/history").json()[0]["id"]

    response = api_client.post(
        "/api/v1/reports",
        json={"source": "history", "history_ids": [history_id, history_id], "format": "csv"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "history"
    assert len(body["hosts"]) == 1
    host = body["hosts"][0]
    assert (host["name"], host["machine_id"], host["device_count"]) == ("Local API", None, 1)
    assert datetime.fromisoformat(host["scanned_at"]) == datetime.fromisoformat(
        scanned.json()["scanned_at"].replace("Z", "+00:00")
    )
    rows = _csv_rows(api_client, body["filename"])
    assert [row["Host"] for row in rows] == ["Local API"]
    assert rows[0]["Grade"] == recorded_grade


def test_history_report_validation(api_client: TestClient) -> None:
    missing = api_client.post(
        "/api/v1/reports",
        json={"source": "history", "history_ids": ["20260926-120000-deadbeef"]},
    )
    assert missing.status_code == 404
    assert "not found" in missing.json()["detail"].lower()

    for ids in (None, []):
        response = api_client.post("/api/v1/reports", json={"source": "history", "history_ids": ids})
        assert response.status_code == 400

    too_many = [f"20260926-120000-{i:08x}" for i in range(51)]
    response = api_client.post("/api/v1/reports", json={"source": "history", "history_ids": too_many})
    assert response.status_code == 400


def test_fleet_report_without_devices_is_400(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _register(api_client, "bench-01", "10.0.0.9:8844")
    _forbid_local_scans(monkeypatch)
    response = api_client.post("/api/v1/reports", json={"source": "fleet"})
    assert response.status_code == 400
    assert response.json()["detail"] == "No saved scans to report on — run Scan all hosts first"
    assert api_client.get("/api/v1/reports").json() == []


def test_fresh_scan_report_keeps_single_host_layout(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/reports", json={"format": "html", "mock_file": str(MOCK_NVME_FILE)})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "scan"
    assert body["hosts"][0]["name"] == "Local API"
    assert body["hosts"][0]["device_count"] == 1
    html = api_client.get(f"/api/v1/reports/{body['filename']}").text
    assert "Source: Fresh scan on this bench" in html
    assert "<th>Host</th>" not in html
    assert 'title="Host"' not in html


def test_report_index_persists_across_restart(api_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api.app import create_app

    first = TestClient(create_app())
    csv_report = first.post("/api/v1/reports", json={"format": "csv", "mock_file": str(MOCK_NVME_FILE)})
    html_report = first.post("/api/v1/reports", json={"format": "html", "mock_file": str(MOCK_NVME_FILE)})
    assert csv_report.status_code == 200 and html_report.status_code == 200
    # Same-second default names must not collide.
    assert csv_report.json()["filename"] != html_report.json()["filename"]

    index_path = api_env / "reports" / "index.json"
    assert stat.S_IMODE(os.stat(index_path).st_mode) == 0o600

    restarted = TestClient(create_app())
    listed = restarted.get("/api/v1/reports")
    assert listed.status_code == 200
    entries = listed.json()
    assert [e["filename"] for e in entries] == [html_report.json()["filename"], csv_report.json()["filename"]]
    assert entries[0]["source"] == "scan"
    assert entries[0]["devices_count"] == 1
    assert entries[0]["hosts"][0]["name"] == "Local API"
    assert set(entries[0]) == {"filename", "format", "generated_at", "source", "devices_count", "hosts"}

    download = restarted.get(f"/api/v1/reports/{entries[1]['filename']}?download=true")
    assert download.status_code == 200
    assert "attachment" in download.headers["content-disposition"]


def test_report_index_is_capped(tmp_path: Path) -> None:
    from cdi_health.api.reports_index import ReportIndexStore

    store = ReportIndexStore(tmp_path, max_entries=3)
    (tmp_path / "reports").mkdir()
    for i in range(5):
        path = tmp_path / "reports" / f"r{i}.csv"
        path.write_text("x", encoding="utf-8")
        store.add(
            {
                "filename": path.name,
                "output_file": str(path),
                "format": "csv",
                "generated_at": f"2026-09-26T12:00:0{i}+00:00",
                "source": "fleet",
                "devices_count": 1,
                "hosts": [],
            }
        )
    assert [r["filename"] for r in store.list()] == ["r4.csv", "r3.csv", "r2.csv"]
    # Dropped records never delete report files.
    assert (tmp_path / "reports" / "r0.csv").is_file()


# --- self-tests forwarded to remote benches ---------------------------------


def test_forwarded_selftest_start_status_jobs_abort(api_client: TestClient, bench: FakeBench) -> None:
    machine = _register(api_client, "bench-01", bench.address)
    runtime = api_client.app.state.runtime
    # The local hardware lock is never taken for forwarded calls.
    assert runtime.hardware_lock.acquire(blocking=False)
    try:
        started = api_client.post(
            "/api/v1/selftests",
            json={"machine_id": machine["id"], "device": "/dev/nvme0", "test_type": "extended"},
        )
    finally:
        runtime.hardware_lock.release()
    assert started.status_code == 200, started.text
    assert started.json()["job_id"] == "remote-job-1"
    assert started.json()["machine_id"] == machine["id"]
    sent = bench.last()
    assert sent["path"] == "/api/v1/selftests"
    assert sent["headers"]["x-api-token"] == REMOTE_TOKEN
    assert "machine_id" not in sent["body"]
    assert sent["body"]["device"] == "/dev/nvme0"
    assert sent["body"]["test_type"] == "extended"
    assert runtime.job_store.list(limit=10, offset=0) == []

    status = api_client.get("/api/v1/selftests/status", params={"machine_id": machine["id"], "device": "/dev/nvme0"})
    assert status.status_code == 200
    assert status.json() == {**REMOTE_STATUS, "machine_id": machine["id"]}
    assert bench.last()["path"] == "/api/v1/selftests/status?device=%2Fdev%2Fnvme0"

    jobs = api_client.get("/api/v1/jobs", params={"machine_id": machine["id"], "limit": 5})
    assert jobs.status_code == 200
    assert [(j["job_id"], j["machine_id"]) for j in jobs.json()] == [("remote-job-1", machine["id"])]
    assert bench.last()["path"] == "/api/v1/jobs?limit=5&offset=0"

    job = api_client.get("/api/v1/jobs/remote-job-1", params={"machine_id": machine["id"]})
    assert job.status_code == 200
    assert job.json()["status"] == "running"
    assert job.json()["machine_id"] == machine["id"]
    assert "machine_id" not in bench.last()["path"]

    missing = api_client.get("/api/v1/jobs/nope", params={"machine_id": machine["id"]})
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Job not found"

    aborted = api_client.post("/api/v1/selftests/abort", json={"machine_id": machine["id"], "device": "/dev/nvme0"})
    assert aborted.status_code == 200
    assert aborted.json() == {"device": "/dev/nvme0", "aborted": True, "machine_id": machine["id"]}
    assert bench.last()["body"] == {"device": "/dev/nvme0"}

    assert api_client.get(f"/api/v1/machines/{machine['id']}").json()["status"] == "reachable"


def test_forwarded_selftest_to_no_auth_bench_sends_no_token(api_client: TestClient) -> None:
    no_auth = FakeBench(token=None)
    try:
        machine = _register(api_client, "lab", no_auth.address, token=None)
        response = api_client.get("/api/v1/selftests/status", params={"machine_id": machine["id"]})
        assert response.status_code == 200
        assert "x-api-token" not in no_auth.last()["headers"]
    finally:
        no_auth.stop()


def test_forwarded_selftest_errors(api_client: TestClient, bench: FakeBench) -> None:
    down = _register(api_client, "down", f"127.0.0.1:{_closed_port()}")
    response = api_client.post("/api/v1/selftests", json={"machine_id": down["id"]})
    assert response.status_code == 502
    assert "unreachable" in response.json()["detail"]
    assert api_client.get(f"/api/v1/machines/{down['id']}").json()["status"] == "unreachable"

    wrong = _register(api_client, "wrong-token", bench.address, token="nope")
    response = api_client.get("/api/v1/jobs", params={"machine_id": wrong["id"]})
    assert response.status_code == 502
    assert "token" in response.json()["detail"]
    assert api_client.get(f"/api/v1/machines/{wrong['id']}").json()["status"] == "auth_failed"

    public = _register(api_client, "public", "8.8.8.8:8844")
    response = api_client.get("/api/v1/selftests/status", params={"machine_id": public["id"]})
    assert response.status_code == 400

    unknown = api_client.post("/api/v1/selftests/abort", json={"machine_id": "missing", "device": "/dev/nvme0"})
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "Machine not found"

    bad_device = api_client.get(
        "/api/v1/selftests/status", params={"machine_id": wrong["id"], "device": "/dev/nvme0;id"}
    )
    assert bad_device.status_code == 400


def test_selftest_machine_without_address_runs_locally(api_client: TestClient, bench: FakeBench) -> None:
    local = _register(api_client, "this-bench", "", token=None)
    status = api_client.get("/api/v1/selftests/status", params={"machine_id": local["id"]})
    assert status.status_code == 200
    assert status.json() == api_client.get("/api/v1/selftests/status").json()

    started = api_client.post("/api/v1/selftests", json={"machine_id": local["id"]})
    assert started.status_code == 200, started.text
    job_id = started.json()["job_id"]
    assert started.json()["machine_id"] is None
    assert "machine_id" not in started.json()["payload"]
    local_job = api_client.get(f"/api/v1/jobs/{job_id}", params={"machine_id": local["id"]})
    assert local_job.status_code == 200
    assert any(j["job_id"] == job_id for j in api_client.get("/api/v1/jobs").json())
    assert bench.requests == []
