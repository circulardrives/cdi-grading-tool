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

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cdi_health.api.schemas import ReportRequest, ScanRequest, SelfTestStartRequest
from cdi_health.classes.config import configure_thresholds
from cdi_health.classes.nvme_selftest import NVMeSelfTest
from cdi_health.classes.reporter import ReportGenerator
from cdi_health.classes.scoring import HealthScoreCalculator
from cdi_health.cli import check_prerequisites, scan_devices_mock, scan_devices_real, scan_single_mock


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _serialize(value: Any) -> Any:
    """Convert values recursively to JSON-safe structures."""
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _decode(value: bytes | str | None) -> str:
    """Decode command output/errors to a clean string."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return value.strip()


def _enrich_devices_with_scores(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach health scoring fields to device dictionaries."""
    calculator = HealthScoreCalculator()
    enriched: list[dict[str, Any]] = []
    for device in devices:
        score = calculator.calculate(device)
        payload = dict(device)
        payload.update(score.to_dict())
        enriched.append(_serialize(payload))
    return enriched


def run_scan(request: ScanRequest) -> dict[str, Any]:
    """Execute a device scan and return structured JSON data."""
    if request.config:
        configure_thresholds(request.config)

    mock_mode = bool(request.mock_data or request.mock_file)
    if mock_mode:
        if request.mock_file:
            devices = scan_single_mock(request.mock_file)
        elif request.mock_data:
            devices = scan_devices_mock(
                request.mock_data,
                ignore_ata=request.ignore_ata,
                ignore_nvme=request.ignore_nvme,
                ignore_scsi=request.ignore_scsi,
            )
        else:
            devices = []
    else:
        missing_tools = check_prerequisites(
            ignore_ata=request.ignore_ata,
            ignore_nvme=request.ignore_nvme,
            ignore_scsi=request.ignore_scsi,
        )
        if missing_tools:
            raise RuntimeError(f"Missing required tools: {', '.join(missing_tools)}")

        devices = scan_devices_real(
            ignore_ata=request.ignore_ata,
            ignore_nvme=request.ignore_nvme,
            ignore_scsi=request.ignore_scsi,
        )

    if request.device:
        devices = [d for d in devices if d.get("dut") == request.device]

    enriched = _enrich_devices_with_scores(devices)
    healthy = sum(1 for d in enriched if d.get("health_score", 0) >= 75)
    warning = sum(1 for d in enriched if 40 <= d.get("health_score", 0) < 75)
    failed = sum(1 for d in enriched if d.get("health_score", 0) < 40)

    return {
        "scanned_at": utc_now().isoformat(),
        "summary": {
            "total": len(enriched),
            "healthy": healthy,
            "warning": warning,
            "failed": failed,
        },
        "devices": enriched,
    }


def _supported_nvme_targets(device: str | None = None) -> list[dict[str, Any]]:
    """Return supported target metadata for a specific device or all devices."""
    if device:
        targets = [{"device": device, "supported": False}]
        try:
            handler = NVMeSelfTest(device)
            targets[0]["supported"] = handler.is_supported()
            targets[0]["handler"] = handler if targets[0]["supported"] else None
        except Exception:
            targets[0]["handler"] = None
        return targets

    return NVMeSelfTest.find_supported_devices()


def _read_latest_selftest_result(handler: NVMeSelfTest) -> dict[str, bool]:
    """Get latest pass/fail/abort state from self-test results."""
    outcome = {"passed": False, "failed": False, "aborted": False}
    try:
        results = handler.get_results()
        entries = results.get("entries", [])
        valid_entries = [e for e in entries if e.get("result") in (0, 1, 2) and e.get("type") in (1, 2)]
        if not valid_entries:
            return outcome

        latest = valid_entries[0]
        result = latest.get("result")
        if result == 0:
            outcome["passed"] = True
        elif result == 1:
            outcome["failed"] = True
        elif result == 2:
            outcome["aborted"] = True
    except Exception:
        return outcome
    return outcome


def run_selftest_start(request: SelfTestStartRequest) -> dict[str, Any]:
    """Start NVMe self-tests and optionally wait for completion."""
    targets = _supported_nvme_targets(request.device)
    if not targets:
        return {"devices": [], "summary": {"total": 0, "started": 0, "completed": 0, "failed_to_start": 0}}

    if request.device and not request.device.startswith("/dev/nvme"):
        raise ValueError("Self-test only supports NVMe controller paths (e.g., /dev/nvme0)")

    results: list[dict[str, Any]] = []
    handlers: dict[str, NVMeSelfTest] = {}

    for target in targets:
        device_path = target.get("device")
        supported = bool(target.get("supported"))
        handler = target.get("handler")

        entry: dict[str, Any] = {
            "device": device_path,
            "test_type": request.test_type,
            "supported": supported,
            "started": False,
            "in_progress": False,
            "completed": False,
            "passed": False,
            "failed": False,
            "aborted": False,
            "status": "not_supported" if not supported else "ready",
            "error": None,
            "last_test_date": None,
        }

        if not supported or handler is None:
            results.append(entry)
            continue

        try:
            cmd = handler.execute_short() if request.test_type == "short" else handler.execute_extended()
            if cmd.return_code == 0:
                entry["started"] = True
                entry["in_progress"] = True
                entry["status"] = "started"
                handlers[device_path] = handler
            else:
                error_msg = _decode(cmd.errors) or "Unknown error"
                if "in progress" in error_msg.lower() or "0x411d" in error_msg:
                    entry["started"] = True
                    entry["in_progress"] = True
                    entry["status"] = "already_running"
                    handlers[device_path] = handler
                else:
                    entry["status"] = "start_failed"
                    entry["error"] = error_msg
        except Exception as exc:
            entry["status"] = "start_failed"
            entry["error"] = str(exc)

        results.append(entry)

    if request.wait:
        deadline = time.monotonic() + request.timeout_seconds
        pending = {r["device"] for r in results if r.get("started") and r.get("in_progress")}

        while pending and time.monotonic() < deadline:
            time.sleep(request.poll_interval_seconds)
            for result in results:
                device_path = result["device"]
                if device_path not in pending:
                    continue
                handler = handlers.get(device_path)
                if handler is None:
                    pending.discard(device_path)
                    continue
                try:
                    status = handler.get_current_status()
                    result["status"] = status.get("status", "unknown")
                    in_progress = bool(status.get("in_progress", False))
                    result["in_progress"] = in_progress
                    if in_progress:
                        continue

                    result["completed"] = True
                    pending.discard(device_path)
                    outcome = _read_latest_selftest_result(handler)
                    result.update(outcome)
                    last_test = handler.get_last_test_date()
                    if last_test:
                        result["last_test_date"] = last_test.isoformat()
                except Exception as exc:
                    result["in_progress"] = False
                    result["completed"] = True
                    result["status"] = "status_check_failed"
                    result["error"] = str(exc)
                    pending.discard(device_path)

        if pending:
            for result in results:
                if result["device"] in pending:
                    result["status"] = "timeout"
                    result["error"] = f"Timed out after {request.timeout_seconds} seconds"
                    result["in_progress"] = True

    started = sum(1 for r in results if r.get("started"))
    completed = sum(1 for r in results if r.get("completed"))
    failed_to_start = sum(1 for r in results if r.get("status") == "start_failed")

    return {
        "devices": _serialize(results),
        "summary": {
            "total": len(results),
            "started": started,
            "completed": completed,
            "failed_to_start": failed_to_start,
        },
    }


def get_selftest_status(device: str | None = None) -> dict[str, Any]:
    """Return current self-test status for one or all NVMe devices."""
    targets = _supported_nvme_targets(device)
    statuses = []

    for target in targets:
        device_path = target.get("device")
        supported = bool(target.get("supported"))
        handler = target.get("handler")
        status_entry: dict[str, Any] = {
            "device": device_path,
            "supported": supported,
            "status": "not_supported" if not supported else "unknown",
            "in_progress": False,
            "passed": False,
            "failed": False,
            "aborted": False,
            "last_test_date": None,
            "error": None,
        }

        if not supported or handler is None:
            statuses.append(status_entry)
            continue

        try:
            current = handler.get_current_status()
            status_entry["status"] = current.get("status", "unknown")
            status_entry["in_progress"] = bool(current.get("in_progress", False))
            status_entry.update(_read_latest_selftest_result(handler))
            last_test = handler.get_last_test_date()
            if last_test:
                status_entry["last_test_date"] = last_test.isoformat()
        except Exception as exc:
            status_entry["status"] = "error"
            status_entry["error"] = str(exc)

        statuses.append(status_entry)

    return {"devices": _serialize(statuses), "total": len(statuses)}


def abort_selftest(device: str) -> dict[str, Any]:
    """Abort active self-test on a specific NVMe device."""
    if not device.startswith("/dev/nvme"):
        raise ValueError("Abort requires an NVMe controller path (e.g., /dev/nvme0)")

    handler = NVMeSelfTest(device)
    if not handler.is_supported():
        raise RuntimeError(f"Device {device} does not support NVMe self-test")

    cmd = handler.abort()
    if cmd.return_code != 0:
        raise RuntimeError(_decode(cmd.errors) or "Failed to abort self-test")

    return {"device": device, "aborted": True}


def generate_report(request: ReportRequest) -> dict[str, Any]:
    """Generate HTML/PDF report from the latest scan request options."""
    scan_request = ScanRequest(
        ignore_ata=request.ignore_ata,
        ignore_nvme=request.ignore_nvme,
        ignore_scsi=request.ignore_scsi,
        device=request.device,
        config=request.config,
        mock_data=request.mock_data,
        mock_file=request.mock_file,
    )
    scan_result = run_scan(scan_request)
    devices = scan_result["devices"]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if request.output_file:
        output_path = Path(request.output_file).expanduser()
    else:
        output_path = Path.cwd() / "reports" / f"cdi-report-{timestamp}.{request.format}"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reporter = ReportGenerator()
    if request.format == "html":
        reporter.generate_html(devices, str(output_path))
    elif request.format == "csv":
        reporter.generate_csv(devices, str(output_path))
    else:
        reporter.generate_pdf(devices, str(output_path))

    return {
        "generated_at": utc_now().isoformat(),
        "output_file": str(output_path.resolve()),
        "format": request.format,
        "devices_count": len(devices),
    }
