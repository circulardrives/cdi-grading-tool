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

"""
NVMe Self-Test Support

Implements NVMe Device Self-Test functionality per NVMe Base Specification 2.3.
Supports short and extended self-tests via nvme-cli.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timedelta
from typing import Any

from cdi_health.classes.exceptions import CommandException
from cdi_health.classes.tools import Command

# Strict NVMe controller/namespace paths — reject whitespace and injected tokens.
_NVME_DEVICE_RE = re.compile(r"^/dev/nvme[0-9]+(n[0-9]+)?$")


def validate_nvme_device_path(device_path: str) -> str:
    """Reject device paths that could inject extra nvme-cli arguments."""
    if not device_path or not _NVME_DEVICE_RE.fullmatch(device_path):
        raise ValueError(f"Invalid NVMe device path; expected /dev/nvmeN or /dev/nvmeNnN (got {device_path!r})")
    return device_path


# ---------------------------------------------------------------------------
# Device Self-test log (Log Page 06h) decoding — NVMe Base Specification
# ---------------------------------------------------------------------------
#
# Layout: 4-byte header followed by 20 Self-test Result Data Structures of
# 28 bytes each (newest first).
#
# Header:  byte 0 bits 3:0 = Current Device Self-test Operation
#          byte 1 bits 6:0 = Current Device Self-test Completion (%)
# Entry:   byte 0 bits 3:0 = Self-test Result, bits 7:4 = Self-test Code
#          byte 1 = Segment Number, byte 2 = Valid Diagnostic Information
#          bytes 4-11 = Power On Hours (LE u64), 12-15 = NSID,
#          16-23 = Failing LBA, 24 = Status Code Type, 25 = Status Code,
#          26-27 = Vendor Specific

LOG_06H_HEADER_LEN = 4
LOG_06H_ENTRY_LEN = 28
LOG_06H_MAX_ENTRIES = 20
LOG_06H_LEN = LOG_06H_HEADER_LEN + LOG_06H_ENTRY_LEN * LOG_06H_MAX_ENTRIES  # 564

# Self-test Result (entry byte 0, bits 3:0)
RESULT_NO_ERROR = 0x0
RESULT_ABORTED_DST_COMMAND = 0x1
RESULT_ABORTED_CONTROLLER_RESET = 0x2
RESULT_ABORTED_NAMESPACE_REMOVED = 0x3
RESULT_ABORTED_FORMAT_NVM = 0x4
RESULT_FATAL_ERROR = 0x5
RESULT_UNKNOWN_SEGMENT_FAILED = 0x6
RESULT_SEGMENT_FAILED = 0x7
RESULT_ABORTED_UNKNOWN = 0x8
RESULT_ABORTED_SANITIZE = 0x9
RESULT_UNUSED = 0xF

FAILED_RESULT_CODES = frozenset({RESULT_FATAL_ERROR, RESULT_UNKNOWN_SEGMENT_FAILED, RESULT_SEGMENT_FAILED})
ABORTED_RESULT_CODES = frozenset(
    {
        RESULT_ABORTED_DST_COMMAND,
        RESULT_ABORTED_CONTROLLER_RESET,
        RESULT_ABORTED_NAMESPACE_REMOVED,
        RESULT_ABORTED_FORMAT_NVM,
        RESULT_ABORTED_UNKNOWN,
        RESULT_ABORTED_SANITIZE,
    }
)

RESULT_STRINGS = {
    RESULT_NO_ERROR: "Success",
    RESULT_ABORTED_DST_COMMAND: "Aborted: Device Self-test command",
    RESULT_ABORTED_CONTROLLER_RESET: "Aborted: Controller Level Reset",
    RESULT_ABORTED_NAMESPACE_REMOVED: "Aborted: namespace removed",
    RESULT_ABORTED_FORMAT_NVM: "Aborted: Format NVM command",
    RESULT_FATAL_ERROR: "Failed: fatal or unknown test error",
    RESULT_UNKNOWN_SEGMENT_FAILED: "Failed: unknown segment failed",
    RESULT_SEGMENT_FAILED: "Failed: one or more segments failed",
    RESULT_ABORTED_UNKNOWN: "Aborted: unknown reason",
    RESULT_ABORTED_SANITIZE: "Aborted: sanitize operation",
    RESULT_UNUSED: "Entry not used",
}

# Self-test Code (entry byte 0 bits 7:4, and current operation)
CODE_SHORT = 0x1
CODE_EXTENDED = 0x2
CODE_VENDOR = 0xE
SELF_TEST_CODE_STRINGS = {CODE_SHORT: "Short", CODE_EXTENDED: "Extended", CODE_VENDOR: "Vendor specific"}
IN_PROGRESS_OPERATIONS = frozenset({CODE_SHORT, CODE_EXTENDED, CODE_VENDOR})

# Valid Diagnostic Information flags (entry byte 2)
VDI_NSID = 0x1
VDI_FLBA = 0x2
VDI_SCT = 0x4
VDI_SC = 0x8


def classify_result(result: int | None) -> str:
    """Map a Self-test Result nibble to passed / failed / aborted / unused / unknown."""
    if result is None:
        return "unknown"
    if result == RESULT_NO_ERROR:
        return "passed"
    if result in FAILED_RESULT_CODES:
        return "failed"
    if result in ABORTED_RESULT_CODES:
        return "aborted"
    if result == RESULT_UNUSED:
        return "unused"
    return "unknown"  # reserved codes Ah-Eh


def decode_dsts(value: int) -> tuple[int, int]:
    """Split entry byte 0 into (Self-test Result, Self-test Code)."""
    return value & 0x0F, (value >> 4) & 0x0F


def _op_string(op_value: int) -> str:
    if op_value == 0:
        return "No self-test in progress"
    if op_value == CODE_SHORT:
        return "Short self-test in progress"
    if op_value == CODE_EXTENDED:
        return "Extended self-test in progress"
    if op_value == CODE_VENDOR:
        return "Vendor specific self-test in progress"
    return f"Unknown operation ({op_value})"


def _make_entry(
    result: int,
    code: int | None,
    *,
    segment: int | None = None,
    vdi: int = 0,
    power_on_hours: int | None = None,
    nsid: int | None = None,
    failing_lba: int | None = None,
    sct: int | None = None,
    sc: int | None = None,
) -> dict[str, Any]:
    return {
        "result": result,
        "result_string": RESULT_STRINGS.get(result, f"Reserved ({result})"),
        "status": classify_result(result),
        "type": code,
        "type_string": SELF_TEST_CODE_STRINGS.get(code, f"Unknown ({code})") if code is not None else "Unknown",
        "segment": segment,
        "valid_diagnostic_info": vdi,
        "power_on_hours": power_on_hours,
        # Legacy alias kept for API consumers: this is power-on hours, NOT a timestamp.
        "completion_time": power_on_hours if power_on_hours is not None else 0,
        "nsid": nsid,
        "failing_lba": failing_lba,
        "status_code_type": sct,
        "status_code": sc,
    }


def _log_result(op_value: int, completion: int, entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "current_self_test_operation": {"value": op_value, "string": _op_string(op_value)},
        "current_self_test_completion": completion,
        "in_progress": op_value in IN_PROGRESS_OPERATIONS,
        "entries": entries,
    }


def parse_self_test_log_bytes(data: bytes) -> dict[str, Any]:
    """
    Decode a raw Device Self-test log (Log Page 06h).

    Unused entries (result Fh) are skipped; entry order (newest first) is preserved.
    """
    if len(data) < LOG_06H_HEADER_LEN:
        return _log_result(0, 0, [])

    op_value = data[0] & 0x0F
    completion = data[1] & 0x7F
    entries: list[dict[str, Any]] = []

    for idx in range(LOG_06H_MAX_ENTRIES):
        off = LOG_06H_HEADER_LEN + idx * LOG_06H_ENTRY_LEN
        raw = data[off : off + LOG_06H_ENTRY_LEN]
        if len(raw) < LOG_06H_ENTRY_LEN:
            break
        result, code = decode_dsts(raw[0])
        if result == RESULT_UNUSED:
            continue
        vdi = raw[2]
        entries.append(
            _make_entry(
                result,
                code,
                segment=raw[1],
                vdi=vdi,
                power_on_hours=int.from_bytes(raw[4:12], "little"),
                nsid=int.from_bytes(raw[12:16], "little") if vdi & VDI_NSID else None,
                failing_lba=int.from_bytes(raw[16:24], "little") if vdi & VDI_FLBA else None,
                sct=raw[24] if vdi & VDI_SCT else None,
                sc=raw[25] if vdi & VDI_SC else None,
            )
        )

    return _log_result(op_value, completion, entries)


_HEX_LINE_RE = re.compile(r"^[0-9a-fA-F]+:")
_HEX_BYTE_RE = re.compile(r"^[0-9a-fA-F]{2}$")


def parse_hex_dump(text: str) -> bytes:
    """Extract bytes from an nvme-cli hex dump ("0000: 00 01 ... \"....\"")."""
    out = bytearray()
    for line in text.splitlines():
        line = line.strip()
        if not _HEX_LINE_RE.match(line):
            continue
        hex_part = line.split(":", 1)[1].split('"')[0]
        out.extend(int(tok, 16) for tok in hex_part.split() if _HEX_BYTE_RE.match(tok))
    return bytes(out)


def _parse_int(value: str) -> int | None:
    """Parse the first token of an nvme-cli value ("0x7", "12", "45%", "0x1 (Short)")."""
    tokens = value.strip().split()
    if not tokens:
        return None
    tok = tokens[0].rstrip("%,;")
    try:
        if tok.lower().startswith("0x"):
            return int(tok, 16)
        return int(tok, 10)
    except ValueError:
        return None


_TEXT_ENTRY_SPLIT_RE = re.compile(r"^\s*Self Test Result\s*\[\s*\d+\s*\]\s*:", re.MULTILINE)


def parse_self_test_log_text(text: str) -> dict[str, Any] | None:
    """
    Parse ``nvme self-test-log`` text output.

    nvme-cli prints header values and entry fields with ``%#x`` (e.g. ``0x1``),
    and "Operation Result"/"Self Test Code" are the already-split nibbles of
    entry byte 0. If a value larger than 0xF appears (raw byte), it is split
    per spec. Returns None when the output is not recognisable.
    """
    op_match = re.search(r"Current operation\s*:\s*(\S+)", text, re.IGNORECASE)
    if not op_match:
        return None
    op_raw = _parse_int(op_match.group(1)) or 0
    op_value = op_raw & 0x0F
    comp_match = re.search(r"Current Completion\s*:\s*(\S+)", text, re.IGNORECASE)
    completion = (_parse_int(comp_match.group(1)) or 0) & 0x7F if comp_match else 0

    entries: list[dict[str, Any]] = []
    for block in _TEXT_ENTRY_SPLIT_RE.split(text)[1:]:
        fields: dict[str, int | None] = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields[key.strip().lower()] = _parse_int(value)

        result = fields.get("operation result")
        if result is None:
            continue
        code = fields.get("self test code")
        if result > 0x0F:  # raw DSTS byte
            result, embedded_code = decode_dsts(result)
            if code is None:
                code = embedded_code
        if code is not None and code > 0x0F:
            code = decode_dsts(code)[1]
        if result == RESULT_UNUSED:
            continue

        poh = next((v for k, v in fields.items() if k.startswith("power on hours")), None)
        entries.append(
            _make_entry(
                result,
                code,
                segment=fields.get("failing segment", fields.get("segment number")),
                vdi=fields.get("valid diagnostic information") or 0,
                power_on_hours=poh,
                nsid=fields.get("namespace identifier"),
                failing_lba=fields.get("failing lba"),
                sct=fields.get("status code type"),
                sc=fields.get("status code"),
            )
        )

    return _log_result(op_value, completion, entries)


def _entry_key(entry: dict[str, Any]) -> tuple:
    return tuple(
        entry.get(k)
        for k in (
            "result",
            "type",
            "segment",
            "power_on_hours",
            "nsid",
            "failing_lba",
            "status_code_type",
            "status_code",
        )
    )


def find_new_entry(
    before: list[dict[str, Any]] | None,
    after: list[dict[str, Any]],
    expected_code: int | None = None,
) -> dict[str, Any] | None:
    """
    Return the newest log entry if it was added after ``before`` was captured.

    A new entry is detected when the number of used entries grew, or (log full
    at 20 entries) the entry list shifted. The newest entry must not predate the
    baseline's newest entry (POH) and, if ``expected_code`` is given, must have
    that Self-test Code. Returns None when no new entry can be confirmed.
    """
    if before is None or not after:
        return None
    newest = after[0]
    if expected_code is not None and newest.get("type") != expected_code:
        return None
    if before:
        prev_poh = before[0].get("power_on_hours")
        new_poh = newest.get("power_on_hours")
        if prev_poh is not None and new_poh is not None and new_poh < prev_poh:
            return None
    before_keys = [_entry_key(e) for e in before]
    after_keys = [_entry_key(e) for e in after]
    if len(after_keys) > len(before_keys) or after_keys != before_keys:
        return newest
    return None


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).replace(",", "").strip(), 0)
    except ValueError:
        return None


class NVMeSelfTest:
    """
    NVMe Self-Test Management

    Per NVMe Base Specification 2.3:
    - Short Device Self-Test (DSTS code 1)
    - Extended Device Self-Test (DSTS code 2)
    - Abort Device Self-Test (DSTS code 0xF)
    - Get Device Self-Test Results (Log Page 0x06)
    """

    # Self-test codes per NVMe spec 2.3
    DSTS_ABORT = 0xF
    DSTS_SHORT = 0x1
    DSTS_EXTENDED = 0x2

    def __init__(self, device_path: str):
        """
        Initialize NVMe Self-Test handler.

        :param device_path: NVMe device path (e.g., /dev/nvme0)
        """
        self.device_path = validate_nvme_device_path(device_path)
        self.nvme_path = self._find_nvme_cli()

    def _find_nvme_cli(self) -> str:
        """Find nvme-cli binary."""
        nvme_path = shutil.which("nvme")
        if not nvme_path:
            raise CommandException("nvme-cli not found. Please install nvme-cli.")
        return nvme_path

    @staticmethod
    def find_nvme_devices() -> list[str]:
        """
        Find all NVMe devices on the system.

        :return: List of NVMe device paths (e.g., ['/dev/nvme0', '/dev/nvme1'])
        """
        nvme_path = shutil.which("nvme")
        if not nvme_path:
            return []

        try:
            cmd = Command(f"{nvme_path} list -o json")
            cmd.run()

            if cmd.return_code != 0:
                return []

            output_str = cmd.output.decode("utf-8") if isinstance(cmd.output, bytes) else cmd.output
            data = json.loads(output_str)

            devices = []
            seen_controllers = set()

            for dev in data.get("Devices", []):
                device_path = dev.get("DevicePath", "")
                # Extract controller path (e.g., /dev/nvme0 from /dev/nvme0n1)
                if device_path.startswith("/dev/nvme"):
                    # Find the controller (e.g., /dev/nvme0 from /dev/nvme0n1)
                    # Pattern: /dev/nvme<number>n<namespace>
                    import re

                    match = re.match(r"(/dev/nvme\d+)", device_path)
                    if match:
                        controller = match.group(1)
                        if controller not in seen_controllers:
                            devices.append(controller)
                            seen_controllers.add(controller)

            return sorted(devices)
        except Exception as e:
            # Fallback: try lsblk or /dev/nvme*
            import glob
            import os

            nvme_devices = []
            for path in glob.glob("/dev/nvme[0-9]*"):
                # Check if it's a controller (not a namespace)
                if os.path.exists(path) and not os.path.exists(f"{path}n1"):
                    # It's likely a controller
                    nvme_devices.append(path)
            return sorted(nvme_devices)

    @staticmethod
    def find_supported_devices() -> list[dict]:
        """
        Find all NVMe devices that support self-test.

        :return: List of dicts with device path and support status
        """
        devices = []
        nvme_devices = NVMeSelfTest.find_nvme_devices()

        for device_path in nvme_devices:
            try:
                selftest = NVMeSelfTest(device_path)
                supported = selftest.is_supported()
                devices.append(
                    {
                        "device": device_path,
                        "supported": supported,
                        "handler": selftest if supported else None,
                    }
                )
            except Exception:
                devices.append(
                    {
                        "device": device_path,
                        "supported": False,
                        "handler": None,
                    }
                )

        return devices

    def is_supported(self) -> bool:
        """
        Check if device supports self-test.

        :return: True if self-test is supported
        """
        try:
            # Check if device supports self-test via identify controller
            cmd = Command(f"sudo {self.nvme_path} id-ctrl {self.device_path} -o json")
            cmd.run()

            if cmd.return_code != 0:
                return False

            try:
                data = json.loads(cmd.output.decode("utf-8"))
                # Check Optional Admin Commands - bit 4 indicates self-test support
                oacs = data.get("oacs", 0)
                # Bit 4 (0x10) = Device Self-Test supported
                return bool(oacs & 0x10)
            except (json.JSONDecodeError, KeyError):
                return False
        except Exception:
            return False

    def execute_short(self) -> Command:
        """
        Execute short device self-test.

        Per NVMe spec: Short self-test should complete in minutes.

        :return: Command object with execution results
        """
        cmd_str = f"sudo {self.nvme_path} device-self-test {self.device_path} --self-test-code={self.DSTS_SHORT}"
        cmd = Command(cmd_str)
        cmd.run()
        return cmd

    def execute_extended(self) -> Command:
        """
        Execute extended device self-test.

        Per NVMe spec: Extended self-test performs comprehensive testing
        and may take hours depending on device capacity.

        :return: Command object with execution results
        """
        cmd_str = f"sudo {self.nvme_path} device-self-test {self.device_path} --self-test-code={self.DSTS_EXTENDED}"
        cmd = Command(cmd_str)
        cmd.run()
        return cmd

    def abort(self) -> Command:
        """
        Abort running device self-test.

        :return: Command object with execution results
        """
        cmd_str = f"sudo {self.nvme_path} device-self-test {self.device_path} --self-test-code={self.DSTS_ABORT}"
        cmd = Command(cmd_str)
        cmd.run()
        return cmd

    def get_status_via_command(self) -> dict:
        """
        Get current self-test status using device-self-test command with code 0.

        This is an alternative method to get status.

        :return: Dictionary with current status
        """
        # Try with JSON first
        cmd_str = f"sudo {self.nvme_path} device-self-test {self.device_path} --self-test-code=0 -o json"
        cmd = Command(cmd_str)
        cmd.run()

        if cmd.return_code == 0 and cmd.output:
            try:
                output_str = cmd.output.decode("utf-8") if isinstance(cmd.output, bytes) else cmd.output
                # Check if it's valid JSON
                if output_str.strip().startswith("{"):
                    data = json.loads(output_str)
                    return data
            except json.JSONDecodeError:
                pass

        # Try without JSON (text output)
        cmd_str = f"sudo {self.nvme_path} device-self-test {self.device_path} --self-test-code=0"
        cmd = Command(cmd_str)
        cmd.run()

        if cmd.return_code == 0 and cmd.output:
            output_str = cmd.output.decode("utf-8") if isinstance(cmd.output, bytes) else cmd.output
            output_lower = output_str.lower().strip()

            # Parse text output - nvme-cli returns:
            # "no self test running" when no test
            # "progress X%" when test is running
            if "progress" in output_lower:
                # Extract percentage if available
                import re

                percent_match = re.search(r"(\d+)%", output_str)
                percent = int(percent_match.group(1)) if percent_match else 0

                # Determine test type from log page or assume short
                # (We can't tell from this command alone, but short is more common)
                return {
                    "status": 1,  # Assume short (most common)
                    "message": f"Self-test in progress ({percent}%)",
                    "percent": percent,
                    "in_progress": True,
                }
            elif "no self test" in output_lower or "not running" in output_lower:
                return {
                    "status": 0,
                    "message": "No self-test in progress",
                    "in_progress": False,
                }

        return {}

    def get_results(self) -> dict:
        """
        Get device self-test results from Log Page 06h.

        Uses 'nvme self-test-log' text output (preferred) or a raw 'nvme get-log'
        hex dump as fallback. Both are decoded per the NVMe Base Specification;
        unused entries (result Fh) are omitted and entries are newest first.

        :return: Dictionary with current operation, completion, and entries
        """
        cmd = Command(f"sudo {self.nvme_path} self-test-log {self.device_path}")
        cmd.run()

        if cmd.return_code == 0 and cmd.output:
            output_str = cmd.output.decode("utf-8") if isinstance(cmd.output, bytes) else cmd.output
            parsed = parse_self_test_log_text(output_str)
            if parsed is not None:
                return parsed

        # Fallback: raw log page as a hex dump
        cmd = Command(f"sudo {self.nvme_path} get-log {self.device_path} --log-id=0x06 --log-len={LOG_06H_LEN}")
        cmd.run()

        if cmd.return_code != 0:
            error_msg = cmd.errors.decode("utf-8") if cmd.errors else "Unknown error"
            # Some devices may not support self-test log - return empty structure
            if "Invalid" in error_msg or "not supported" in error_msg.lower() or "not found" in error_msg.lower():
                result = _log_result(0, 0, [])
                result["current_self_test_operation"]["string"] = "Self-test not supported"
                return result
            raise CommandException(f"Failed to get self-test log: {error_msg}")

        output_str = ""
        if cmd.output:
            output_str = cmd.output.decode("utf-8") if isinstance(cmd.output, bytes) else cmd.output
        data = parse_hex_dump(output_str)
        if len(data) < LOG_06H_HEADER_LEN:
            result = _log_result(0, 0, [])
            result["current_self_test_operation"]["string"] = "No self-test data available"
            return result
        return parse_self_test_log_bytes(data)

    def get_current_status(self) -> dict:
        """
        Get current self-test status.

        Tries multiple methods to get status:
        1. Use device-self-test command with code 0 (most reliable)
        2. Get self-test log (Log Page 0x06) for detailed info

        :return: Dictionary with current status information
        """
        # First try device-self-test command (more reliable for current status)
        try:
            status_data = self.get_status_via_command()
            if status_data and isinstance(status_data, dict):
                # Check if test is in progress
                if status_data.get("in_progress", False):
                    status_value = status_data.get("status", 1)  # Default to short
                    percent = status_data.get("percent", 0)
                    message = status_data.get("message", "Self-test in progress")

                    return {
                        "status": message,
                        "value": status_value,
                        "in_progress": True,
                        "percent": percent,
                        "entries": [],
                    }
                else:
                    # No test running
                    return {
                        "status": status_data.get("message", "No self-test in progress"),
                        "value": 0,
                        "in_progress": False,
                        "entries": [],
                    }
        except Exception:
            pass

        # Fallback to log page
        try:
            results = self.get_results()
            current_op = results.get("current_self_test_operation", {})
            status = current_op.get("string", "Unknown")
            value = current_op.get("value", 0)

            # Current operation: 0 = none, 1 = short, 2 = extended, Eh = vendor specific
            in_progress = value in IN_PROGRESS_OPERATIONS

            return {
                "status": status,
                "value": value,
                "in_progress": in_progress,
                "entries": results.get("entries", []),
            }
        except CommandException:
            pass

        # Return default if both methods fail
        return {
            "status": "Unable to determine status",
            "value": 0,
            "in_progress": False,
            "entries": [],
        }

    @staticmethod
    def _op_value_to_string(op_value: int) -> str:
        """Convert current-operation value to string."""
        return _op_string(op_value)

    @staticmethod
    def _result_to_string(result: int) -> str:
        """Convert a Self-test Result code to string."""
        return RESULT_STRINGS.get(result, f"Reserved ({result})")

    @staticmethod
    def _type_to_string(test_type: int) -> str:
        """Convert a Self-test Code to string."""
        return SELF_TEST_CODE_STRINGS.get(test_type, f"Unknown ({test_type})")

    def get_power_on_hours(self) -> int | None:
        """
        Current controller Power On Hours from the SMART / Health log (02h).

        :return: Power-on hours, or None if unavailable
        """
        try:
            cmd = Command(f"sudo {self.nvme_path} smart-log {self.device_path} -o json")
            cmd.run()
            if cmd.return_code != 0 or not cmd.output:
                return None
            output_str = cmd.output.decode("utf-8") if isinstance(cmd.output, bytes) else cmd.output
            data = json.loads(output_str)
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        return _coerce_int(data.get("power_on_hours"))

    def get_last_test_power_on_hours(self) -> int | None:
        """
        Power On Hours recorded in the newest self-test log entry.

        :return: POH of the most recent self-test, or None if no entries
        """
        entries = self.get_results().get("entries", [])
        if not entries:
            return None
        return _coerce_int(entries[0].get("power_on_hours"))

    def hours_since_last_test(self) -> int | None:
        """
        Power-on hours elapsed since the newest self-test (current POH - entry POH).

        :return: Hours, or None if unknown
        """
        test_poh = self.get_last_test_power_on_hours()
        if test_poh is None:
            return None
        current_poh = self.get_power_on_hours()
        if current_poh is None or current_poh < test_poh:
            return None
        return current_poh - test_poh

    def get_failed_tests(self, days: int = 90) -> list[dict]:
        """
        Get failed self-tests (results 5, 6, 7) within the look-back window.

        The log only records Power On Hours, so the window is ``days * 24``
        power-on hours before the controller's current POH. This is a superset
        of the wall-clock window (the drive may have been powered off). If the
        current POH cannot be read, all failed entries are returned.

        :param days: Number of days to look back (default: 90)
        :return: List of failed test entries
        """
        entries = self.get_results().get("entries", [])
        failed = [e for e in entries if classify_result(e.get("result")) == "failed"]
        if not failed:
            return []

        current_poh = self.get_power_on_hours()
        if current_poh is None:
            return failed

        cutoff_poh = current_poh - days * 24
        return [
            e
            for e in failed
            if _coerce_int(e.get("power_on_hours")) is None or _coerce_int(e.get("power_on_hours")) >= cutoff_poh
        ]

    def has_recent_failures(self, days: int = 90) -> bool:
        """
        Check if device has recent failed self-tests.

        :param days: Number of days to check (default: 90)
        :return: True if failures found
        """
        return len(self.get_failed_tests(days)) > 0

    def get_last_test_date(self) -> datetime | None:
        """
        Estimate the date of the last self-test.

        Self-test entries carry Power On Hours, not a timestamp, so the date is
        estimated as ``now - (current POH - entry POH)``. Because POH does not
        advance while the drive is powered off, the true date may be earlier.

        :return: Estimated datetime of last test, or None if unknown
        """
        hours = self.hours_since_last_test()
        if hours is None:
            return None
        return datetime.now() - timedelta(hours=hours)

    def days_since_last_test(self) -> int | None:
        """
        Power-on days since the last self-test (lower bound on wall-clock days).

        :return: Days since last test or None if unknown
        """
        hours = self.hours_since_last_test()
        if hours is None:
            return None
        return hours // 24
