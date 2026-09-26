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

"""API hardening tests: per-request thresholds, hardware lock, auth, path allowlist."""

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
def data_dir(tmp_path: Path) -> Path:
    path = tmp_path / "api-data"
    path.mkdir()
    return path


@pytest.fixture
def api_client(data_dir: Path) -> TestClient:
    os.environ["CDI_HEALTH_API_ALLOW_NON_ROOT"] = "1"
    os.environ["CDI_HEALTH_API_MOCK_DATA"] = str(MOCK_DATA_PATH)
    os.environ["CDI_HEALTH_DATA_DIR"] = str(data_dir)
    os.environ.pop("CDI_HEALTH_API_TOKEN", None)
    os.environ.pop("CDI_HEALTH_API_BIND_HOST", None)

    from cdi_health.api.app import create_app

    return TestClient(create_app())


def _runtime(client: TestClient):
    return client.app.state.runtime


# ---------------------------------------------------------------------------
# #136: per-request thresholds never leak into the process-global config
# ---------------------------------------------------------------------------


def test_request_config_does_not_mutate_global_thresholds(api_client: TestClient, data_dir: Path) -> None:
    from cdi_health.classes.config import ThresholdConfig, get_config

    before = get_config()
    custom = data_dir / "binary.yaml"
    custom.write_text("grading:\n  profile: binary\n", encoding="utf-8")

    scoped = api_client.post("/api/v1/scan", json={"mock_file": str(MOCK_NVME_FILE), "config": str(custom)})
    assert scoped.status_code == 200, scoped.text
    assert {d["grading_profile"] for d in scoped.json()["devices"]} == {"binary"}

    # Global singleton is the same object and still on the default profile.
    assert ThresholdConfig._instance is before
    assert get_config().grading_profile == "abcdf"

    default = api_client.post("/api/v1/scan", json={"mock_file": str(MOCK_NVME_FILE)})
    assert default.status_code == 200
    assert {d["grading_profile"] for d in default.json()["devices"]} == {"abcdf"}


def test_scoped_thresholds_restores_previous_instance_on_error() -> None:
    from cdi_health.api.services import scoped_thresholds
    from cdi_health.classes.config import ThresholdConfig

    previous = ThresholdConfig.get_instance()
    replacement = ThresholdConfig()
    with pytest.raises(RuntimeError):
        with scoped_thresholds(replacement):
            assert ThresholdConfig._instance is replacement
            raise RuntimeError("boom")
    assert ThresholdConfig._instance is previous


# ---------------------------------------------------------------------------
# #136: hardware lock -> HTTP 409 while another operation touches drives
# ---------------------------------------------------------------------------


def test_hardware_busy_returns_409_for_device_operations(api_client: TestClient) -> None:
    runtime = _runtime(api_client)
    assert runtime.hardware_lock.acquire(blocking=False)
    try:
        responses = [
            api_client.post("/api/v1/scan", json={"mock_data": str(MOCK_DATA_PATH)}),
            api_client.get("/api/v1/devices?refresh=true"),
            api_client.post("/api/v1/reports", json={"format": "csv", "mock_data": str(MOCK_DATA_PATH)}),
            api_client.post("/api/v1/selftests", json={"test_type": "short"}),
        ]
        for response in responses:
            assert response.status_code == 409, response.text
            assert "busy" in response.json()["detail"].lower()
        assert runtime.selftest_inflight == 0
    finally:
        runtime.hardware_lock.release()

    ok = api_client.post("/api/v1/scan", json={"mock_data": str(MOCK_DATA_PATH)})
    assert ok.status_code == 200


def test_hardware_lock_released_after_failed_scan(api_client: TestClient) -> None:
    missing = MOCK_DATA_PATH / "nvme" / "does-not-exist.json"
    failed = api_client.post("/api/v1/scan", json={"mock_file": str(missing)})
    assert failed.status_code >= 400
    assert not _runtime(api_client).hardware_lock.locked()


def test_selftest_job_releases_hardware_lock(api_client: TestClient) -> None:
    started = api_client.post("/api/v1/selftests", json={"test_type": "short"})
    assert started.status_code == 200
    job_id = started.json()["job_id"]
    for _ in range(40):
        status = api_client.get(f"/api/v1/jobs/{job_id}").json()["status"]
        if status in {"completed", "failed"}:
            break
        time.sleep(0.05)
    runtime = _runtime(api_client)
    for _ in range(40):
        if not runtime.hardware_lock.locked():
            break
        time.sleep(0.05)
    assert not runtime.hardware_lock.locked()


def test_selftest_start_releases_lock_before_wait_polling(monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import services
    from cdi_health.api.schemas import SelfTestStartRequest

    events: list[str] = []

    class FakeCmd:
        return_code = 0
        errors = b""

    class FakeHandler:
        def execute_short(self):
            events.append("start")
            return FakeCmd()

        def get_current_status(self):
            events.append("poll")
            return {"status": "completed", "in_progress": False}

        def get_results(self):
            return {"entries": []}

        def get_last_test_date(self):
            return None

    monkeypatch.setattr(
        services,
        "_supported_nvme_targets",
        lambda device=None: [{"device": "/dev/nvme0", "supported": True, "handler": FakeHandler()}],
    )
    monkeypatch.setattr(services.time, "sleep", lambda _s: None)

    request = SelfTestStartRequest(test_type="short", wait=True, poll_interval_seconds=5, timeout_seconds=60)
    services.run_selftest_start(request, on_started=lambda: events.append("released"))
    assert events == ["start", "released", "poll"]


def test_selftest_saturation_does_not_take_hardware_lock(api_client: TestClient) -> None:
    from cdi_health.api.app import SELFTEST_MAX_WORKERS

    runtime = _runtime(api_client)
    runtime.selftest_inflight = SELFTEST_MAX_WORKERS
    try:
        response = api_client.post("/api/v1/selftests", json={"test_type": "short"})
        assert response.status_code == 503
        assert not runtime.hardware_lock.locked()
    finally:
        runtime.selftest_inflight = 0


def test_api_state_has_no_unused_executor(api_client: TestClient) -> None:
    assert not hasattr(_runtime(api_client), "executor")


# ---------------------------------------------------------------------------
# #131: API scans apply Revert §13/§15 fields; UNGRADED is not "failed"
# ---------------------------------------------------------------------------


def _patch_scan_with_ungraded(monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import services
    from cdi_health.classes.devices import Devices

    healthy = services.scan_single_mock(str(MOCK_NVME_FILE))
    ungraded = Devices._ungraded_placeholder(
        {
            "name": "/dev/sdz",
            "open_error": "Security locked",
            "serial_number": "LOCKED001",
            "protocol": "ATA",
        }
    )

    def fake_scan_devices_mock(path, ignore_ata=False, ignore_nvme=False, ignore_scsi=False):
        return [*healthy, ungraded]

    monkeypatch.setattr(services, "scan_devices_mock", fake_scan_devices_mock)


def test_scan_reports_ungraded_drive_separately(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scan_with_ungraded(monkeypatch)

    response = api_client.post("/api/v1/scan", json={"mock_data": str(MOCK_DATA_PATH)})
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["summary"]["total"] == 2
    assert body["summary"]["ungraded"] == 1
    assert body["summary"]["failed"] == 0
    assert body["grading_profile"] == "abcdf"

    by_serial = {d["serial_number"]: d for d in body["devices"]}
    locked = by_serial["LOCKED001"]
    assert locked["grading_status"] == "UNGRADED"
    assert locked["final_grade"] == "UNGRADED"
    assert locked["health_grade"] == "UNGRADED"
    assert locked["health_score"] is None
    assert locked["fail_reason_codes"]
    assert locked["recommended_use"] == "Manual review required"

    graded = next(d for d in body["devices"] if d["serial_number"] != "LOCKED001")
    for key in ("grading_status", "final_grade", "warning_flags", "fail_reason_codes", "revert_standard_version"):
        assert key in graded
    assert graded["grading_status"] == "GRADED"

    history = api_client.get("/api/v1/history").json()
    assert history[0]["summary"]["ungraded"] == 1
    assert history[0]["summary"]["failed"] == 0
    assert history[0]["grades"].get("UNGRADED") == 1
    assert "F" not in history[0]["grades"]

    detail = api_client.get(f"/api/v1/history/{history[0]['id']}").json()
    stored = {d["serial_number"]: d for d in detail["devices"]}["LOCKED001"]
    assert stored["final_grade"] == "UNGRADED"


def test_machine_summary_tracks_ungraded(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scan_with_ungraded(monkeypatch)
    machine_id = api_client.post("/api/v1/machines", json={"name": "Bench", "hostname": "bench-01"}).json()["id"]
    scanned = api_client.post("/api/v1/scan", json={"mock_data": str(MOCK_DATA_PATH), "machine_id": machine_id})
    assert scanned.status_code == 200
    machine = api_client.get(f"/api/v1/machines/{machine_id}").json()
    assert machine["last_scan_summary"]["ungraded"] == 1
    assert machine["last_scan_summary"]["failed"] == 0


def test_scan_grading_profile_is_per_request(api_client: TestClient) -> None:
    from cdi_health.classes.config import get_config

    binary = api_client.post("/api/v1/scan", json={"mock_file": str(MOCK_NVME_FILE), "grading_profile": "binary"})
    assert binary.status_code == 200, binary.text
    assert binary.json()["grading_profile"] == "binary"
    assert {d["grading_profile"] for d in binary.json()["devices"]} == {"binary"}
    assert get_config().grading_profile == "abcdf"

    default = api_client.post("/api/v1/scan", json={"mock_file": str(MOCK_NVME_FILE)})
    assert default.json()["grading_profile"] == "abcdf"

    history = api_client.get("/api/v1/history").json()
    assert {entry["grading_profile"] for entry in history} == {"binary", "abcdf"}


def test_scan_rejects_unknown_grading_profile(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/scan", json={"mock_file": str(MOCK_NVME_FILE), "grading_profile": "xyz"})
    assert response.status_code == 422


def test_report_accepts_grading_profile(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/reports",
        json={"format": "csv", "mock_file": str(MOCK_NVME_FILE), "grading_profile": "binary"},
    )
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# #132: discovery never leaks this bench's API token to LAN hosts
# ---------------------------------------------------------------------------


class _FakeHealthResponse:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return b'{"status": "ok", "version": "x"}'


def _capture_probe_headers(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    from cdi_health.api import discovery

    captured: list[dict[str, str]] = []

    def fake_urlopen(request, timeout=None):
        captured.append({k.lower(): v for k, v in request.header_items()})
        return _FakeHealthResponse()

    monkeypatch.setattr(discovery.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(discovery, "is_port_open", lambda ip, port, timeout: ip == "192.168.50.1")
    monkeypatch.setattr(discovery, "reverse_hostname", lambda ip: None)
    return captured


def test_discovery_does_not_send_env_token_without_probe_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import discovery

    monkeypatch.setenv("CDI_HEALTH_API_TOKEN", "bench-secret")
    captured = _capture_probe_headers(monkeypatch)

    result = discovery.discover_hosts(subnet="192.168.50.0/30", timeout_seconds=0.5)
    assert result["found"] and result["found"][0]["cdi_api"] is True
    assert captured, "expected one health probe"
    for headers in captured:
        assert "x-api-token" not in headers


def test_discovery_sends_explicit_probe_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import discovery

    monkeypatch.setenv("CDI_HEALTH_API_TOKEN", "bench-secret")
    captured = _capture_probe_headers(monkeypatch)

    discovery.discover_hosts(subnet="192.168.50.0/30", timeout_seconds=0.5, probe_token="remote-token")
    assert [h.get("x-api-token") for h in captured] == ["remote-token"]


def test_discover_endpoint_without_probe_token_sends_no_header(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _capture_probe_headers(monkeypatch)
    monkeypatch.setenv("CDI_HEALTH_API_TOKEN", "bench-secret")

    response = api_client.post(
        "/api/v1/discover",
        json={"subnet": "192.168.50.0/30", "timeout_seconds": 0.5},
        headers={"X-API-Token": "bench-secret"},
    )
    assert response.status_code == 200, response.text
    assert captured and all("x-api-token" not in h for h in captured)


# ---------------------------------------------------------------------------
# #138: constant-time token compare, data-path allowlist, deploy hardening
# ---------------------------------------------------------------------------


def test_tokens_match_uses_constant_time_compare(monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api import security

    calls: list[tuple[bytes, bytes]] = []
    real = security.hmac.compare_digest

    def spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(security.hmac, "compare_digest", spy)
    assert security.tokens_match("s3cret", "s3cret") is True
    assert security.tokens_match("s3cret-x", "s3cret") is False
    assert security.tokens_match(None, "s3cret") is False
    # Non-ASCII input must not raise (str compare_digest would TypeError).
    assert security.tokens_match("tökén", "s3cret") is False
    assert len(calls) == 3


def test_token_auth_accepts_valid_and_rejects_invalid(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CDI_HEALTH_API_ALLOW_NON_ROOT", "1")
    monkeypatch.setenv("CDI_HEALTH_DATA_DIR", str(data_dir))
    monkeypatch.setenv("CDI_HEALTH_API_TOKEN", "correct-horse")
    monkeypatch.delenv("CDI_HEALTH_API_BIND_HOST", raising=False)
    from cdi_health.api.app import create_app

    client = TestClient(create_app())
    assert client.get("/api/v1/history").status_code == 401
    assert client.get("/api/v1/history", headers={"X-API-Token": "correct-hors"}).status_code == 401
    assert client.get("/api/v1/history", headers={"X-API-Token": "correct-horse"}).status_code == 200


def test_resolve_data_path_allows_known_roots(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api.services import resolve_data_path

    monkeypatch.setenv("CDI_HEALTH_DATA_DIR", str(data_dir))
    assert resolve_data_path(str(MOCK_NVME_FILE)) == str(MOCK_NVME_FILE.resolve())
    assert Path(resolve_data_path("src/cdi_health/mock_data")) == MOCK_DATA_PATH.resolve()

    in_data_dir = data_dir / "custom.yaml"
    in_data_dir.write_text("grading:\n  profile: binary\n", encoding="utf-8")
    assert resolve_data_path(str(in_data_dir)) == str(in_data_dir.resolve())


def test_resolve_data_path_rejects_paths_outside_allowlist(
    tmp_path: Path, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cdi_health.api.services import resolve_data_path

    monkeypatch.setenv("CDI_HEALTH_DATA_DIR", str(data_dir))
    monkeypatch.delenv("CDI_HEALTH_API_ALLOWED_DATA_PATHS", raising=False)
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.yaml"
    secret.write_text("x: 1\n", encoding="utf-8")

    for bad in (str(secret), str(outside), "/root/.ssh/id_rsa", "/etc/shadow"):
        with pytest.raises(ValueError, match="outside the allowed"):
            resolve_data_path(bad)

    # A symlink inside an allowed root that points outside is rejected too.
    link = data_dir / "escape.yaml"
    link.symlink_to(secret)
    with pytest.raises(ValueError, match="outside the allowed"):
        resolve_data_path(str(link))

    with pytest.raises(ValueError, match="traversal"):
        resolve_data_path(str(data_dir / ".." / "outside" / "secret.yaml"))


def test_resolve_data_path_extra_roots_env(tmp_path: Path, data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cdi_health.api.services import resolve_data_path

    extra = tmp_path / "datasets"
    extra.mkdir()
    monkeypatch.setenv("CDI_HEALTH_DATA_DIR", str(data_dir))
    monkeypatch.setenv("CDI_HEALTH_API_ALLOWED_DATA_PATHS", str(extra))
    assert resolve_data_path(str(extra)) == str(extra.resolve())


def test_scan_rejects_mock_and_config_outside_allowlist(api_client: TestClient, tmp_path: Path) -> None:
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    cfg = outside / "thresholds.yaml"
    cfg.write_text("grading:\n  profile: binary\n", encoding="utf-8")

    for payload in (
        {"mock_data": str(outside)},
        {"mock_file": str(cfg)},
        {"mock_file": str(MOCK_NVME_FILE), "config": str(cfg)},
    ):
        response = api_client.post("/api/v1/scan", json=payload)
        assert response.status_code == 400, (payload, response.text)
        assert response.json()["detail"] == "Path is outside the allowed data directories"

    report = api_client.post("/api/v1/reports", json={"format": "csv", "config": str(cfg)})
    assert report.status_code == 400
    assert not _runtime(api_client).hardware_lock.locked()


def _read_repo_file(*parts: str) -> str:
    return (REPO_ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_systemd_unit_is_sandboxed() -> None:
    unit = _read_repo_file("deploy", "systemd", "cdi-health-api.service")
    directives = {
        line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip()
        for line in unit.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    assert directives["ProtectSystem"] == "strict"
    assert directives["ProtectHome"] == "true"
    assert directives["PrivateTmp"] == "true"
    assert directives["NoNewPrivileges"] == "true"
    assert "/var/lib/cdi-health" in directives["ReadWritePaths"]
    # The service must reach raw block devices.
    assert "PrivateDevices" not in directives
    # Data dir passed to the API must be writable under ProtectSystem=strict.
    assert "--data-dir /var/lib/cdi-health" in directives["ExecStart"]


def test_sudoers_profile_has_no_wildcard_tool_access() -> None:
    policy = _read_repo_file("deploy", "sudoers", "cdi-health-technician")
    rules = [line for line in policy.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    joined = "\n".join(rules)
    for tool in ("smartctl", "nvme"):
        assert f"/{tool} *" not in joined
    for dangerous in ("format", "sanitize", "security-send", "--set", "fw-download", "write"):
        assert dangerous not in joined
    assert "openSeaChest" not in joined


# ---------------------------------------------------------------------------
# #139: API reports the real package version
# ---------------------------------------------------------------------------


def test_api_reports_package_version(api_client: TestClient) -> None:
    from cdi_health.cli import __version__

    health = api_client.get("/api/v1/health").json()
    assert health["version"] == __version__
    assert api_client.app.version == __version__
    assert api_client.get("/openapi.json").json()["info"]["version"] == __version__
