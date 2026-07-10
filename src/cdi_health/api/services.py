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

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_REPORT_EXTENSIONS = {".html", ".pdf", ".csv"}

from cdi_health.api.machines import resolve_data_dir
from cdi_health.api.schemas import (
    NVME_DEVICE_PATTERN,
    ReportRequest,
    ScanRequest,
    SelfTestStartRequest,
)
from cdi_health.classes.config import configure_thresholds
from cdi_health.classes.nvme_selftest import NVMeSelfTest, validate_nvme_device_path
from cdi_health.classes.reporter import ReportGenerator
from cdi_health.classes.scoring import HealthScoreCalculator
from cdi_health.cli import (
    _filter_devices_by_path,
    check_prerequisites,
    scan_devices_mock,
    scan_devices_real,
    scan_single_mock,
)

DEFAULT_MOCK_DATA_ENV = "CDI_HEALTH_API_MOCK_DATA"


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def weasyprint_available() -> bool:
    """Return True when PDF generation dependency is importable."""
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        return False
    return True


def reports_directory() -> Path:
    """Return the dedicated reports output directory under the API data dir."""
    path = resolve_data_dir() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def validate_report_filename(filename: str) -> None:
    """Reject unsafe or unsupported report download filenames."""
    if not filename or filename != Path(filename).name:
        raise ValueError("Invalid report filename")
    if ".." in filename or filename.startswith("."):
        raise ValueError("Invalid report filename")
    if Path(filename).suffix.lower() not in ALLOWED_REPORT_EXTENSIONS:
        raise ValueError("Unsupported report format")


def resolve_report_output_path(output_file: str | None, report_format: str) -> Path:
    """
    Resolve a report output path constrained to the dedicated reports directory.

    Accepts a basename, a relative path under the reports dir, or an absolute
    path that resolves inside the allowlisted directory. Rejects traversal and
    symlink escapes.
    """
    reports_dir = reports_directory()
    if output_file:
        candidate = Path(output_file).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            # Basename-only or relative under reports/
            if candidate.name != candidate.as_posix() and ".." in candidate.parts:
                raise ValueError("Report output path must stay within the reports directory")
            resolved = (reports_dir / candidate.name).resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        resolved = (reports_dir / f"cdi-report-{timestamp}.{report_format}").resolve()

    try:
        resolved.relative_to(reports_dir)
    except ValueError as exc:
        raise ValueError("Report output path must stay within the reports directory") from exc

    if resolved.suffix.lower() not in ALLOWED_REPORT_EXTENSIONS:
        raise ValueError("Unsupported report format")

    # Reject if an existing symlink would escape the allowlist after open.
    if resolved.exists() and resolved.is_symlink():
        link_target = resolved.resolve()
        try:
            link_target.relative_to(reports_dir)
        except ValueError as exc:
            raise ValueError("Report output path must stay within the reports directory") from exc

    return resolved


def resolve_report_file(filename: str, registered_paths: set[str] | None = None) -> Path:
    """
    Resolve a report filename to an on-disk path.

    Prefer explicitly registered generation paths; fall back only to the
    dedicated reports directory (never an arbitrary CWD reports/ folder).
    """
    validate_report_filename(filename)
    reports_dir = reports_directory()
    candidates: list[Path] = []

    if registered_paths:
        for path_str in registered_paths:
            candidate = Path(path_str)
            if candidate.name == filename:
                candidates.append(candidate)

    # Scoped fallback: only files under the dedicated reports directory.
    candidates.append(reports_dir / filename)

    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        resolved_key = str(resolved)
        if resolved_key in seen:
            continue
        seen.add(resolved_key)
        try:
            resolved.relative_to(reports_dir)
        except ValueError:
            continue
        if resolved.is_file() and not resolved.is_symlink():
            return resolved
        # Allow regular files reached via a non-escaping path.
        if resolved.is_file():
            return resolved

    raise FileNotFoundError(f"Report not found: {filename}")


def media_type_for_report(filename: str) -> str:
    """Return the HTTP media type for a generated report filename."""
    return {
        ".html": "text/html; charset=utf-8",
        ".pdf": "application/pdf",
        ".csv": "text/csv; charset=utf-8",
    }.get(Path(filename).suffix.lower(), "application/octet-stream")


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


def resolve_data_path(path: str) -> str:
    """Resolve mock/config paths relative to cwd or repository root."""
    candidate = Path(path).expanduser()
    if any(part == ".." for part in candidate.parts):
        raise ValueError("Path traversal is not allowed")
    if candidate.exists():
        return str(candidate.resolve())

    repo_root = Path(__file__).resolve().parents[3]
    repo_relative = repo_root / path
    if any(part == ".." for part in Path(path).parts):
        raise ValueError("Path traversal is not allowed")
    if repo_relative.exists():
        return str(repo_relative.resolve())

    return str(candidate)


def apply_scan_defaults(request: ScanRequest) -> ScanRequest:
    """Apply server default mock data and normalize relative mock paths."""
    updates: dict[str, str] = {}
    if request.mock_data:
        updates["mock_data"] = resolve_data_path(request.mock_data)
    if request.mock_file:
        updates["mock_file"] = resolve_data_path(request.mock_file)

    if not request.mock_data and not request.mock_file:
        default_mock = os.getenv(DEFAULT_MOCK_DATA_ENV)
        if default_mock:
            updates["mock_data"] = resolve_data_path(default_mock)

    if not updates:
        return request
    return request.model_copy(update=updates)


def _enrich_devices_with_scores(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach health scoring fields to device dictionaries."""
    calculator = HealthScoreCalculator()
    enriched: list[dict[str, Any]] = []
    for device in devices:
        score = calculator.calculate(device)
        payload = dict(device)
        payload.update(score.to_dict())
        payload["report_category"] = ReportGenerator._device_report_category(payload)
        enriched.append(_serialize(payload))
    return enriched


def run_scan(request: ScanRequest) -> dict[str, Any]:
    """Execute a device scan and return structured JSON data."""
    request = apply_scan_defaults(request)

    if request.config:
        configure_thresholds(resolve_data_path(request.config))

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
        devices = _filter_devices_by_path(devices, request.device)

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


def _assert_nvme_device(device: str | None) -> None:
    """Re-validate NVMe device paths before invoking nvme-cli wrappers."""
    if device is None:
        return
    if not NVME_DEVICE_PATTERN.fullmatch(device):
        raise ValueError("Self-test only supports NVMe controller paths (e.g., /dev/nvme0)")
    validate_nvme_device_path(device)


def _supported_nvme_targets(device: str | None = None) -> list[dict[str, Any]]:
    """Return supported target metadata for a specific device or all devices."""
    _assert_nvme_device(device)
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


def _serialize_selftest_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize one NVMe self-test log entry for API responses."""
    result_code = entry.get("result")
    type_code = entry.get("type")
    return {
        "result_code": result_code,
        "result": entry.get("result_string") or NVMeSelfTest._result_to_string(result_code or 0),
        "test_type_code": type_code,
        "test_type": entry.get("type_string") or NVMeSelfTest._type_to_string(type_code or 0),
        "completion_time": entry.get("completion_time", 0),
    }


def _read_selftest_outcome(handler: NVMeSelfTest) -> dict[str, Any]:
    """Get pass/fail state and detailed self-test log data from nvme self-test-log."""
    outcome: dict[str, Any] = {
        "passed": False,
        "failed": False,
        "aborted": False,
        "latest_result": None,
        "recent_results": [],
        "current_completion": None,
        "current_operation": None,
        "logs_message": None,
    }
    try:
        results = handler.get_results()
        current_op = results.get("current_self_test_operation", {})
        op_value = current_op.get("value", 0)
        outcome["current_completion"] = results.get("current_self_test_completion")
        outcome["current_operation"] = current_op.get("string") or current_op.get("value")

        entries = results.get("entries", [])
        valid_entries = [e for e in entries if e.get("result") in (0, 1, 2) and e.get("type") in (1, 2)]
        outcome["recent_results"] = [_serialize_selftest_entry(entry) for entry in valid_entries[:5]]

        if not valid_entries:
            if op_value in (1, 2):
                outcome["logs_message"] = "Self-test in progress; NVMe Log Page 0x06 entries appear after completion."
            else:
                outcome["logs_message"] = "No completed self-test entries in NVMe Log Page 0x06."
            return outcome

        latest = valid_entries[0]
        result = latest.get("result")
        if result == 0:
            outcome["passed"] = True
        elif result == 1:
            outcome["failed"] = True
        elif result == 2:
            outcome["aborted"] = True

        outcome["latest_result"] = _serialize_selftest_entry(latest)
    except Exception as exc:
        outcome["logs_message"] = f"Could not read NVMe self-test log: {exc}"
        return outcome
    return outcome


def run_selftest_start(request: SelfTestStartRequest) -> dict[str, Any]:
    """Start NVMe self-tests and optionally wait for completion."""
    _assert_nvme_device(request.device)
    targets = _supported_nvme_targets(request.device)
    if not targets:
        return {"devices": [], "summary": {"total": 0, "started": 0, "completed": 0, "failed_to_start": 0}}

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
                    outcome = _read_selftest_outcome(handler)
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
    if device is not None:
        _assert_nvme_device(device)
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
            if status_entry["in_progress"]:
                status_entry["progress_percent"] = current.get("percent")
            status_entry.update(_read_selftest_outcome(handler))
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
    _assert_nvme_device(device)

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

    output_path = resolve_report_output_path(request.output_file, request.format)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reporter = ReportGenerator()
    if request.format == "html":
        reporter.generate_html(devices, str(output_path))
    elif request.format == "csv":
        reporter.generate_csv(devices, str(output_path))
    else:
        reporter.generate_pdf(devices, str(output_path))

    resolved_path = output_path.resolve()
    return {
        "generated_at": utc_now().isoformat(),
        "output_file": str(resolved_path),
        "filename": resolved_path.name,
        "format": request.format,
        "devices_count": len(devices),
    }


def http_error_detail(exc: Exception, *, context: str) -> tuple[int, str]:
    """
    Map known exceptions to safe client-facing messages.

    Returns (status_code, detail). Unexpected errors become generic 500s;
    full exception text is logged server-side by the caller.
    """
    if isinstance(exc, ValueError):
        message = str(exc)
        # Keep short, actionable validation messages; avoid dumping paths/tool output.
        if len(message) > 200 or any(token in message for token in ("/", "\\", "Traceback")):
            return 400, f"Invalid {context} request"
        return 400, message
    if isinstance(exc, FileNotFoundError):
        return 404, f"{context.capitalize()} not found"
    if isinstance(exc, PermissionError):
        return 403, "Permission denied"
    if isinstance(exc, RuntimeError):
        message = str(exc)
        if message.startswith("Missing required tools:"):
            return 400, message
        return 400, f"{context.capitalize()} failed"
    return 500, f"{context.capitalize()} failed due to an internal error"
