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

"""Export smartctl and optional NVMe CLI JSON for offline mock use."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

_NVME_JSON_TIMEOUT_SEC = 120


def _nvme_namespace_block_path(dut: str) -> str:
    """Block path for nvme-cli (e.g. ``/dev/nvme0`` → ``/dev/nvme0n1``); matches ``NVMeProtocol.nvme_namespace_block_path``."""
    if re.match(r"^/dev/nvme\d+n\d+$", dut):
        return dut
    m = re.match(r"^(/dev/nvme\d+)$", dut)
    if m:
        return f"{m.group(1)}n1"
    return dut


def anonymize_serial(serial: str, index: int) -> str:
    """Anonymize serial number while keeping format."""
    if not serial or serial == "Not Reported":
        return f"MOCK{index:06d}"

    match = re.match(r"^([A-Z]{2,3})(.*)$", serial.upper())
    if match:
        prefix = match.group(1)
        suffix = match.group(2)
        new_suffix = f"{index:06d}"[: len(suffix)] if suffix else f"{index:06d}"
        return f"{prefix}{new_suffix}"

    return f"MOCK{index:06d}"


def anonymize_wwn(wwn_data: dict | None, index: int) -> dict | None:
    """Anonymize WWN data."""
    if not wwn_data:
        return None

    if isinstance(wwn_data, dict):
        return {"naa": wwn_data.get("naa", 5), "oui": wwn_data.get("oui", 3152), "id": 100000000000 + index}
    return wwn_data


def anonymize_json(data: dict[str, Any], index: int, original_serial: str | None = None) -> dict[str, Any]:
    """Anonymize sensitive data in smartctl JSON."""
    data = json.loads(json.dumps(data))

    if original_serial is None:
        original_serial = str(data.get("serial_number", ""))

    anonymized_serial = anonymize_serial(original_serial, index) if original_serial else f"MOCK{index:06d}"

    if "serial_number" in data:
        data["serial_number"] = anonymized_serial

    if "device" in data and isinstance(data["device"], dict):
        if "serial_number" in data["device"]:
            data["device"]["serial_number"] = anonymized_serial

    if "smartctl" in data and isinstance(data["smartctl"], dict):
        if "output" in data["smartctl"] and isinstance(data["smartctl"]["output"], list):
            for i, line in enumerate(data["smartctl"]["output"]):
                if original_serial and original_serial in line:
                    data["smartctl"]["output"][i] = line.replace(original_serial, anonymized_serial)

    if "wwn" in data:
        if isinstance(data["wwn"], dict):
            data["wwn"] = anonymize_wwn(data["wwn"], index)
        elif isinstance(data["wwn"], str) and data["wwn"] != "Not Reported":
            data["wwn"] = f"0x{5000000000000000 + index:016x}"

    if "smart_attributes" in data and isinstance(data["smart_attributes"], list):
        for attr in data["smart_attributes"]:
            if "raw" in attr and isinstance(attr["raw"], dict):
                raw_str = attr["raw"].get("string", "")
                if original_serial and original_serial in raw_str:
                    attr["raw"]["string"] = raw_str.replace(original_serial, anonymized_serial)

    return data


def nvme_controller_from_dut(dut: str) -> str:
    """Return NVMe character-device path (e.g. ``/dev/nvme0`` from ``/dev/nvme0n1``)."""
    m = re.match(r"^(/dev/nvme\d+)", dut)
    if m:
        return m.group(1)
    return dut


def deep_replace_str(obj: Any, old: str, new: str) -> Any:
    """Replace every occurrence of *old* in nested strings (for nvme-cli JSON + log text)."""
    if not old:
        return obj
    if isinstance(obj, str):
        return obj.replace(old, new)
    if isinstance(obj, dict):
        return {k: deep_replace_str(v, old, new) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_replace_str(v, old, new) for v in obj]
    return obj


def _filter_nvme_list_for_device(list_data: dict[str, Any], dut: str) -> dict[str, Any]:
    """Keep only ``Devices`` entries for this controller or namespace (privacy + size)."""
    ctrl = nvme_controller_from_dut(dut)
    devices = list_data.get("Devices") or []
    kept: list[Any] = []
    for d in devices:
        if not isinstance(d, dict):
            continue
        path = str(d.get("DevicePath", ""))
        if path == dut or path.startswith(ctrl):
            kept.append(d)
    out = {k: v for k, v in list_data.items() if k != "Devices"}
    out["Devices"] = kept
    return out


def _run_nvme_json(cmd: list[str]) -> Any | None:
    for attempt in (cmd, ["sudo", *cmd]):
        try:
            r = subprocess.run(
                attempt,
                capture_output=True,
                text=True,
                check=False,
                timeout=_NVME_JSON_TIMEOUT_SEC,
            )
            if r.returncode != 0 or not (r.stdout or "").strip():
                continue
            return json.loads(r.stdout)
        except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
            continue
    return None


def _run_nvme_text(cmd: list[str]) -> str | None:
    for attempt in (cmd, ["sudo", *cmd]):
        try:
            r = subprocess.run(
                attempt,
                capture_output=True,
                text=True,
                check=False,
                timeout=_NVME_JSON_TIMEOUT_SEC,
            )
            if r.returncode != 0 or not (r.stdout or "").strip():
                continue
            return r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def collect_nvme_cli_bundle(device_path: str) -> dict[str, Any]:
    """
    Run nvme-cli for one device and return structured JSON (and self-test text).

    Keys may include: ``list``, ``id_ctrl``, ``id_ns``, ``smart_log``, ``error_log``,
    ``ocp_smart_log`` (OCP SMART Additional Log, page C0h, when supported),
    ``device_self_test``, ``self_test_log_text``.
    """
    if not shutil.which("nvme"):
        return {}

    ctrl = nvme_controller_from_dut(device_path)
    out: dict[str, Any] = {}

    raw_list = _run_nvme_json(["nvme", "list", "-o", "json", device_path])
    if raw_list is None:
        raw_list = _run_nvme_json(["nvme", "list", "-o", "json"])
    if isinstance(raw_list, dict):
        out["list"] = _filter_nvme_list_for_device(raw_list, device_path)

    idc = _run_nvme_json(["nvme", "id-ctrl", ctrl, "-o", "json"])
    if idc is not None:
        out["id_ctrl"] = idc

    if device_path != ctrl:
        idns = _run_nvme_json(["nvme", "id-ns", device_path, "-o", "json"])
        if idns is not None:
            out["id_ns"] = idns

    sm = _run_nvme_json(["nvme", "smart-log", ctrl, "-o", "json"])
    if sm is None and device_path != ctrl:
        sm = _run_nvme_json(["nvme", "smart-log", device_path, "-o", "json"])
    if sm is not None:
        out["smart_log"] = sm

    el = _run_nvme_json(["nvme", "error-log", ctrl, "-o", "json"])
    if el is not None:
        out["error_log"] = el

    ns_path = _nvme_namespace_block_path(device_path)
    ocp = _run_nvme_json(["nvme", "ocp", "smart-add-log", ns_path, "-o", "json"])
    if ocp is not None:
        out["ocp_smart_log"] = ocp

    dst = _run_nvme_json(
        ["nvme", "device-self-test", ctrl, "--self-test-code=0", "-o", "json"],
    )
    if dst is not None:
        out["device_self_test"] = dst

    st_text = _run_nvme_text(["nvme", "self-test-log", ctrl])
    if st_text:
        out["self_test_log_text"] = st_text

    return out


def get_smartctl_json(device: str) -> dict[str, Any] | None:
    """Return parsed smartctl JSON for a device, or None if unavailable."""
    for cmd in (
        ["smartctl", "--xall", "--json=ov", device],
        ["sudo", "smartctl", "--xall", "--json=ov", device],
    ):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    if "json_format_version" not in data:
                        continue
                    if "messages" in data.get("smartctl", {}):
                        messages = data["smartctl"].get("messages", [])
                        errors = [m for m in messages if m.get("severity") == "error"]
                        if errors:
                            continue
                    if "device" in data or "serial_number" in data:
                        return data
                except json.JSONDecodeError:
                    continue
        except FileNotFoundError:
            continue

    return None


def _health_filename_suffix(device_info: dict[str, Any]) -> str:
    if not device_info.get("smart_status", True):
        return "failing_smart"
    if device_info.get("health_grade") == "F":
        return "failing"
    if (device_info.get("reallocated_sectors") or 0) > 10:
        return "high_reallocated"
    if (device_info.get("pending_sectors") or 0) > 10:
        return "high_pending"
    if (device_info.get("uncorrectable_errors") or 0) > 10:
        return "high_uncorrectable"
    return "healthy"


def export_mock_snapshots_to_dir(
    devices: list[dict[str, Any]],
    output_dir: Path | str,
    *,
    anonymize: bool = True,
    progress: Callable[[str], None] | None = None,
) -> tuple[int, int]:
    """
    Write per-device JSON under ``output_dir/<protocol>/``.

    Each file is primarily smartctl ``--xall --json=ov`` output. NVMe devices also
    include a ``nvme_cli`` object (``nvme list``, ``id-ctrl``, ``smart-log``, etc.).

    :param devices: Device dicts from a scan (must include ``dut``, ``transport_protocol``, etc.).
    :param output_dir: Root directory for export.
    :param anonymize: If True, redact serial numbers and WWN (default).
    :param progress: Optional status line callback (default: print).
    :return: ``(written_count, skipped_count)``
    """
    out = Path(output_dir)
    prog: Callable[[str], None] = progress if progress is not None else print

    devices_by_protocol: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for i, device in enumerate(devices):
        protocol = str(device.get("transport_protocol", "unknown")).lower()
        devices_by_protocol[protocol].append((i, device))

    written = 0
    skipped = 0

    for protocol, device_list in devices_by_protocol.items():
        protocol_dir = out / protocol
        protocol_dir.mkdir(parents=True, exist_ok=True)

        for index, device_info in device_list:
            device_path = str(device_info["dut"])
            model = str(device_info.get("model_number", "Unknown"))
            serial = str(device_info.get("serial_number", "Unknown"))

            prog(f"Processing {device_path} ({protocol.upper()}): {model} - {serial}")

            smartctl_data = get_smartctl_json(device_path)
            if not smartctl_data:
                prog(f"  ⚠ Skipping {device_path} (could not get smartctl data)")
                skipped += 1
                continue

            original_serial = str(device_info.get("serial_number", ""))
            payload = json.loads(json.dumps(smartctl_data))

            if protocol == "nvme":
                nvme_bundle = collect_nvme_cli_bundle(device_path)
                if nvme_bundle:
                    payload["nvme_cli"] = nvme_bundle
                    prog(f"  + nvme-cli: {', '.join(sorted(nvme_bundle))}")
                elif not shutil.which("nvme"):
                    prog("  (nvme-cli not in PATH; smartctl-only export for this NVMe device)")

            if anonymize:
                payload = anonymize_json(payload, index, original_serial)
                if "nvme_cli" in payload and original_serial:
                    anon_s = anonymize_serial(original_serial, index)
                    payload["nvme_cli"] = deep_replace_str(payload["nvme_cli"], original_serial, anon_s)

            # NVMeProtocol reads top-level ``ocp_smart_log``; mirror from nvme-cli bundle for mock replay
            nv = payload.get("nvme_cli")
            if isinstance(nv, dict) and isinstance(nv.get("ocp_smart_log"), dict) and nv["ocp_smart_log"]:
                if not payload.get("ocp_smart_log"):
                    payload["ocp_smart_log"] = json.loads(json.dumps(nv["ocp_smart_log"]))

            health_status = _health_filename_suffix(device_info)
            safe_model = re.sub(r"[^a-zA-Z0-9]", "_", model)[:30]
            filename = f"{safe_model}_{health_status}.json"
            filepath = protocol_dir / filename

            if filepath.exists():
                filename = f"{safe_model}_{index}_{health_status}.json"
                filepath = protocol_dir / filename

            filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            written += 1
            rel = filepath
            try:
                rel = filepath.relative_to(Path.cwd())
            except ValueError:
                pass
            prog(f"  ✓ Saved to {rel}")
            if anonymize:
                prog(f"    Anonymized serial: {payload.get('serial_number', 'N/A')}")

    return written, skipped
