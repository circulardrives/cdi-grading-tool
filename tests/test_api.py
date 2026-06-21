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

"""FastAPI endpoint tests (mock data; no real hardware)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
MOCK_DATA_PATH = REPO_ROOT / "src" / "cdi_health" / "mock_data"
MOCK_NVME_FILE = MOCK_DATA_PATH / "nvme" / "SSDPEK1A118GA_healthy.json"


@pytest.fixture
def api_client(tmp_path: Path) -> TestClient:
    """API allows non-root in tests; default mock data enabled."""
    os.environ["CDI_HEALTH_API_ALLOW_NON_ROOT"] = "1"
    os.environ["CDI_HEALTH_API_MOCK_DATA"] = str(MOCK_DATA_PATH)
    os.environ["CDI_HEALTH_DATA_DIR"] = str(tmp_path / "api-data")
    os.environ.pop("CDI_HEALTH_API_TOKEN", None)

    from cdi_health.api.app import create_app

    return TestClient(create_app())


@pytest.fixture
def token_client(tmp_path: Path) -> TestClient:
    """API client with token auth enabled."""
    os.environ["CDI_HEALTH_API_ALLOW_NON_ROOT"] = "1"
    os.environ["CDI_HEALTH_API_MOCK_DATA"] = str(MOCK_DATA_PATH)
    os.environ["CDI_HEALTH_DATA_DIR"] = str(tmp_path / "api-data-token")
    os.environ["CDI_HEALTH_API_TOKEN"] = "test-token"

    from cdi_health.api.app import create_app

    return TestClient(create_app())


def test_api_health_ok(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["allow_non_root_mode"] is True
    assert "weasyprint_available" in body
    assert isinstance(body["weasyprint_available"], bool)


def test_api_scan_mock_data(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/scan",
        json={"mock_data": "src/cdi_health/mock_data"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total"] > 0
    device = body["devices"][0]
    assert "health_score" in device
    assert "health_grade" in device
    assert "report_category" in device
    assert device["report_category"] in {
        "SATA HDD",
        "SAS HDD",
        "SATA SSD",
        "SAS SSD",
        "NVMe SSD",
        "Other",
    }


def test_api_devices_uses_default_mock_when_cache_empty(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/devices")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total"] > 0


def test_api_devices_returns_cached_scan(api_client: TestClient) -> None:
    first = api_client.post(
        "/api/v1/scan",
        json={"mock_data": str(MOCK_DATA_PATH), "ignore_nvme": True},
    )
    assert first.status_code == 200
    first_body = first.json()

    cached = api_client.get("/api/v1/devices")
    assert cached.status_code == 200
    cached_body = cached.json()
    assert cached_body["scanned_at"] == first_body["scanned_at"]
    assert cached_body["summary"] == first_body["summary"]

    refreshed = api_client.get("/api/v1/devices?refresh=true")
    assert refreshed.status_code == 200
    refreshed_body = refreshed.json()

    full_scan = api_client.post(
        "/api/v1/scan",
        json={"mock_data": str(MOCK_DATA_PATH)},
    )
    assert full_scan.status_code == 200
    assert refreshed_body["summary"]["total"] == full_scan.json()["summary"]["total"]


def test_api_scan_device_filter_nvme_alias(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/scan",
        json={
            "mock_file": str(MOCK_NVME_FILE),
            "device": "/dev/nvme1n1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total"] == 1
    assert body["devices"][0]["dut"] == "/dev/nvme1"


def test_api_report_html(api_client: TestClient, tmp_path: Path) -> None:
    output_file = tmp_path / "report.html"
    response = api_client.post(
        "/api/v1/reports",
        json={
            "format": "html",
            "mock_data": str(MOCK_DATA_PATH),
            "output_file": str(output_file),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "html"
    assert body["devices_count"] > 0
    assert Path(body["output_file"]).is_file()
    assert body["filename"] == "report.html"


def test_api_report_download(api_client: TestClient, tmp_path: Path) -> None:
    output_file = tmp_path / "cdi-report-test.html"
    generated = api_client.post(
        "/api/v1/reports",
        json={
            "format": "html",
            "mock_data": str(MOCK_DATA_PATH),
            "output_file": str(output_file),
        },
    )
    assert generated.status_code == 200
    filename = generated.json()["filename"]

    inline = api_client.get(f"/api/v1/reports/{filename}")
    assert inline.status_code == 200
    assert "text/html" in inline.headers["content-type"]
    assert b"<!DOCTYPE html>" in inline.content or b"<html" in inline.content.lower()

    attachment = api_client.get(f"/api/v1/reports/{filename}?download=true")
    assert attachment.status_code == 200
    assert "attachment" in attachment.headers["content-disposition"]


def test_api_report_download_rejects_unsafe_filename(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/reports/../secrets.txt")
    assert response.status_code == 404

    invalid = api_client.get("/api/v1/reports/not-a-report.exe")
    assert invalid.status_code == 400


def test_api_report_download_requires_token(token_client: TestClient, tmp_path: Path) -> None:
    output_file = tmp_path / "cdi-report-token.html"
    generated = token_client.post(
        "/api/v1/reports",
        json={
            "format": "html",
            "mock_data": str(MOCK_DATA_PATH),
            "output_file": str(output_file),
        },
        headers={"X-API-Token": "test-token"},
    )
    assert generated.status_code == 200
    filename = generated.json()["filename"]

    denied = token_client.get(f"/api/v1/reports/{filename}")
    assert denied.status_code == 401

    allowed = token_client.get(
        f"/api/v1/reports/{filename}",
        headers={"X-API-Token": "test-token"},
    )
    assert allowed.status_code == 200


def test_api_report_csv(api_client: TestClient, tmp_path: Path) -> None:
    output_file = tmp_path / "report.csv"
    response = api_client.post(
        "/api/v1/reports",
        json={
            "format": "csv",
            "mock_data": str(MOCK_DATA_PATH),
            "output_file": str(output_file),
        },
    )
    assert response.status_code == 200
    assert Path(response.json()["output_file"]).is_file()


def test_api_token_required(token_client: TestClient) -> None:
    denied = token_client.post("/api/v1/scan", json={})
    assert denied.status_code == 401

    allowed = token_client.post(
        "/api/v1/scan",
        json={},
        headers={"X-API-Token": "test-token"},
    )
    assert allowed.status_code == 200


def test_api_health_does_not_require_token(token_client: TestClient) -> None:
    response = token_client.get("/api/v1/health")
    assert response.status_code == 200


def test_api_selftest_job_lifecycle(api_client: TestClient) -> None:
    status = api_client.get("/api/v1/selftests/status")
    assert status.status_code == 200
    assert "devices" in status.json()

    started = api_client.post(
        "/api/v1/selftests",
        json={"test_type": "short", "wait": False},
    )
    assert started.status_code == 200
    job_id = started.json()["job_id"]

    completed = None
    for _ in range(20):
        job = api_client.get(f"/api/v1/jobs/{job_id}")
        assert job.status_code == 200
        payload = job.json()
        if payload["status"] in {"completed", "failed"}:
            completed = payload
            break
        time.sleep(0.05)

    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["result"] is not None

    jobs = api_client.get("/api/v1/jobs")
    assert jobs.status_code == 200
    assert any(job["job_id"] == job_id for job in jobs.json())


def test_api_selftest_status_includes_result_details(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/selftests/status")
    assert response.status_code == 200
    body = response.json()
    assert "devices" in body
    assert isinstance(body["devices"], list)

    for device in body["devices"]:
        assert "recent_results" in device
        assert "logs_message" in device
        assert isinstance(device["recent_results"], list)
        if not device.get("supported", True):
            continue
        assert "latest_result" in device
        if device.get("latest_result"):
            assert "result_code" in device["latest_result"]
            assert "result" in device["latest_result"]
            assert "test_type" in device["latest_result"]


def test_api_selftest_abort_requires_nvme_path(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/selftests/abort",
        json={"device": "/dev/sda"},
    )
    assert response.status_code == 400


def test_api_machines_crud(api_client: TestClient) -> None:
    created = api_client.post(
        "/api/v1/machines",
        json={
            "name": "Lab Rack A",
            "hostname": "grading-01.local",
            "address": "10.0.0.12:8844",
            "location": "Row 3",
            "notes": "8-bay NVMe",
        },
    )
    assert created.status_code == 200
    body = created.json()
    machine_id = body["id"]
    assert body["name"] == "Lab Rack A"
    assert body["hostname"] == "grading-01.local"
    assert body["status"] == "unknown"
    assert body["last_scan_at"] is None

    listed = api_client.get("/api/v1/machines")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = api_client.get(f"/api/v1/machines/{machine_id}")
    assert detail.status_code == 200
    assert detail.json()["address"] == "10.0.0.12:8844"

    updated = api_client.patch(
        f"/api/v1/machines/{machine_id}",
        json={"location": "Row 4", "status": "reachable"},
    )
    assert updated.status_code == 200
    assert updated.json()["location"] == "Row 4"
    assert updated.json()["status"] == "reachable"

    deleted = api_client.delete(f"/api/v1/machines/{machine_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    missing = api_client.get(f"/api/v1/machines/{machine_id}")
    assert missing.status_code == 404


def test_api_scan_associates_with_machine(api_client: TestClient) -> None:
    created = api_client.post(
        "/api/v1/machines",
        json={"name": "Bench Host", "hostname": "bench-01"},
    )
    machine_id = created.json()["id"]

    scan = api_client.post(
        "/api/v1/scan",
        json={"mock_data": str(MOCK_DATA_PATH), "machine_id": machine_id},
    )
    assert scan.status_code == 200
    scan_body = scan.json()
    assert scan_body["summary"]["total"] > 0

    machine = api_client.get(f"/api/v1/machines/{machine_id}")
    assert machine.status_code == 200
    machine_body = machine.json()
    assert machine_body["last_scan_status"] == "success"
    assert machine_body["last_scan_summary"]["total"] == scan_body["summary"]["total"]
    assert machine_body["status"] == "reachable"

    cached = api_client.get(f"/api/v1/devices?machine_id={machine_id}")
    assert cached.status_code == 200
    assert cached.json()["scanned_at"] == scan_body["scanned_at"]

    missing = api_client.get("/api/v1/devices?machine_id=not-a-host")
    assert missing.status_code == 404


def test_api_scan_unknown_machine_returns_404(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/scan",
        json={"machine_id": "missing-host-id"},
    )
    assert response.status_code == 404


def test_api_machines_require_token(token_client: TestClient) -> None:
    denied = token_client.get("/api/v1/machines")
    assert denied.status_code == 401

    allowed = token_client.get(
        "/api/v1/machines",
        headers={"X-API-Token": "test-token"},
    )
    assert allowed.status_code == 200


def test_discovery_rejects_oversized_subnet(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/discover",
        json={"subnet": "10.0.0.0/8"},
    )
    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


def test_discovery_requires_token(token_client: TestClient) -> None:
    denied = token_client.post("/api/v1/discover", json={"subnet": "192.168.0.0/24"})
    assert denied.status_code == 401

    allowed = token_client.post(
        "/api/v1/discover",
        json={"subnet": "192.168.0.0/24"},
        headers={"X-API-Token": "test-token"},
    )
    assert allowed.status_code in {200, 400}


def test_discovery_finds_mocked_api(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import discovery

    def fake_is_port_open(ip: str, port: int, timeout_seconds: float) -> bool:
        return ip == "192.168.0.1" and port == 8844

    def fake_probe_cdi_health(
        ip: str,
        port: int,
        *,
        probe_token: str | None,
        timeout_seconds: float,
    ) -> dict:
        if ip == "192.168.0.1":
            return {"status": "ok", "is_root": True, "api_token_enabled": False}
        return None

    monkeypatch.setattr(discovery, "is_port_open", fake_is_port_open)
    monkeypatch.setattr(discovery, "probe_cdi_health", fake_probe_cdi_health)
    monkeypatch.setattr(discovery, "reverse_hostname", lambda ip: "grading-01.local")

    response = api_client.post(
        "/api/v1/discover",
        json={"subnet": "192.168.0.0/30", "timeout_seconds": 0.5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scanned_subnets"] == ["192.168.0.0/30"]
    assert body["found"]
    host = body["found"][0]
    assert host["address"] == "192.168.0.1:8844"
    assert host["hostname"] == "grading-01.local"
    assert host["cdi_api"] is True
    assert host["already_registered"] is False


def test_discovery_marks_registered_hosts(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import discovery

    created = api_client.post(
        "/api/v1/machines",
        json={
            "name": "Existing Host",
            "hostname": "192.168.1.1",
            "address": "192.168.1.1:8844",
        },
    )
    assert created.status_code == 200

    monkeypatch.setattr(
        discovery,
        "is_port_open",
        lambda ip, port, timeout_seconds: ip == "192.168.1.1",
    )
    monkeypatch.setattr(
        discovery,
        "probe_cdi_health",
        lambda ip, port, *, probe_token, timeout_seconds: {"status": "ok", "is_root": True},
    )

    response = api_client.post(
        "/api/v1/discover",
        json={"subnet": "192.168.1.0/30", "timeout_seconds": 0.5},
    )
    assert response.status_code == 200
    matches = [item for item in response.json()["found"] if item["ip"] == "192.168.1.1"]
    assert matches
    assert matches[0]["already_registered"] is True


def test_discovery_rate_limited(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import discovery

    monkeypatch.setattr(discovery, "resolve_subnets", lambda subnet, subnets: ["192.168.2.0/30"])
    monkeypatch.setattr(discovery, "parse_subnet", discovery.parse_subnet)
    monkeypatch.setattr(discovery, "is_port_open", lambda ip, port, timeout_seconds: False)

    first = api_client.post(
        "/api/v1/discover",
        json={"subnet": "192.168.2.0/30", "timeout_seconds": 0.5},
    )
    assert first.status_code == 200

    second = api_client.post(
        "/api/v1/discover",
        json={"subnet": "192.168.2.0/30", "timeout_seconds": 0.5},
    )
    assert second.status_code == 429


def test_discovery_unit_helpers() -> None:
    from cdi_health.api.discovery import (
        is_already_registered,
        iter_host_addresses,
        parse_subnet,
    )

    network = parse_subnet("192.168.0.0/30")
    hosts = iter_host_addresses(network)
    assert "192.168.0.1" in hosts
    assert "192.168.0.2" in hosts

    machines = [{"address": "192.168.0.5:8844", "hostname": "rack-a"}]
    assert is_already_registered("192.168.0.5", 8844, machines) is True
    assert is_already_registered("192.168.0.6", 8844, machines) is False
