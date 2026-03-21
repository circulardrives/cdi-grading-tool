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
import shutil
import struct
import subprocess
from datetime import datetime, timedelta
from typing import Any

from cdi_health.classes.exceptions import CommandException
from cdi_health.classes.tools import Command


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
        self.device_path = device_path
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
        Get device self-test results from Log Page 0x06.

        Uses 'nvme self-test-log' command (preferred) or 'nvme get-log' as fallback.

        :return: Dictionary with self-test log data
        """
        # Try self-test-log command first (more reliable, better formatted)
        cmd_str = f"sudo {self.nvme_path} self-test-log {self.device_path}"
        cmd = Command(cmd_str)
        cmd.run()

        if cmd.return_code == 0 and cmd.output:
            output_str = cmd.output.decode("utf-8") if isinstance(cmd.output, bytes) else cmd.output
            # Parse text output from self-test-log command
            parsed = self._parse_self_test_log_text(output_str)
            # Return parsed results (has current operation and entries)
            return parsed

        # Fallback to get-log command (hex dump format)
        cmd_str = f"sudo {self.nvme_path} get-log {self.device_path} --log-id=0x06 --log-len=512"
        cmd = Command(cmd_str)
        cmd.run()

        if cmd.return_code != 0:
            error_msg = cmd.errors.decode("utf-8") if cmd.errors else "Unknown error"
            # Some devices may not support self-test log - return empty structure
            if "Invalid" in error_msg or "not supported" in error_msg.lower() or "not found" in error_msg.lower():
                return {
                    "current_self_test_operation": {
                        "value": 0,
                        "string": "Self-test not supported",
                    },
                    "current_self_test_completion": 0,
                    "entries": [],
                }
            raise CommandException(f"Failed to get self-test log: {error_msg}")

        if not cmd.output:
            return {
                "current_self_test_operation": {
                    "value": 0,
                    "string": "No self-test data available",
                },
                "current_self_test_completion": 0,
                "entries": [],
            }

        # Parse hex dump format
        output_str = cmd.output.decode("utf-8") if isinstance(cmd.output, bytes) else cmd.output

        # nvme-cli hex dump format:
        # 0000: 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f "................"
        # Extract only hex bytes (skip ASCII representation in quotes)
        import re

        all_bytes = []
        for line in output_str.split("\n"):
            line = line.strip()
            # Look for hex dump lines (format: "offset: hex hex hex ...")
            if ":" in line and re.match(r"^[0-9a-fA-F]+:", line):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    # Extract hex bytes before the quote (ASCII representation)
                    # Format: "00 01 02 ..." or "00 01 02 ... " (with trailing space before quote)
                    hex_part = parts[1].split('"')[0].strip()
                    # Extract only valid hex bytes (exactly 2 hex digits, separated by spaces)
                    # Split by space and filter valid 2-digit hex
                    hex_bytes = [
                        b for b in hex_part.split() if len(b) == 2 and all(c in "0123456789abcdefABCDEF" for c in b)
                    ]
                    all_bytes.extend(hex_bytes)

        if len(all_bytes) < 4:
            return {
                "current_self_test_operation": {
                    "value": 0,
                    "string": "No self-test data available",
                },
                "current_self_test_completion": 0,
                "entries": [],
            }

        try:
            # Byte 0: Current self-test operation (0=none, 1=short, 2=extended, 0xF=abort)
            op_value = int(all_bytes[0], 16) if len(all_bytes) > 0 else 0
            # Byte 1: Current self-test completion percentage (0-100)
            completion = int(all_bytes[1], 16) if len(all_bytes) > 1 else 0

            # Parse entries (each entry is 16 bytes, starting at offset 4)
            # Per NVMe spec 2.3, Log Page 0x06 structure:
            # Bytes 0-1: Current operation and completion
            # Bytes 2-3: Reserved
            # Bytes 4-19: Entry 1 (16 bytes)
            # Bytes 20-35: Entry 2 (16 bytes)
            # ... up to 20 entries
            entries = []
            entry_offset = 4  # Start after header (4 bytes)

            while entry_offset + 16 <= len(all_bytes):
                entry_bytes = all_bytes[entry_offset : entry_offset + 16]
                if len(entry_bytes) >= 2:
                    # Byte 0: Result (0=success, 1=fail, 2=aborted)
                    result_val = int(entry_bytes[0], 16)
                    # Byte 1: Test type (1=short, 2=extended)
                    type_val = int(entry_bytes[1], 16)

                    # Only parse valid entries:
                    # - Result must be 0, 1, or 2
                    # - Type must be 1 or 2
                    # - Both cannot be zero (empty slot)
                    if result_val in (0, 1, 2) and type_val in (1, 2) and (result_val != 0 or type_val != 0):
                        # Bytes 8-15: Completion timestamp (little-endian, seconds since power-on)
                        timestamp = 0
                        if len(entry_bytes) >= 16:
                            try:
                                # Convert 8 bytes (bytes 8-15) from little-endian hex
                                timestamp_hex = "".join(reversed(entry_bytes[8:16]))
                                timestamp = int(timestamp_hex, 16) if timestamp_hex else 0
                            except (ValueError, IndexError):
                                pass

                        entries.append(
                            {
                                "result": result_val,
                                "result_string": self._result_to_string(result_val),
                                "type": type_val,
                                "type_string": self._type_to_string(type_val),
                                "completion_time": timestamp,
                            }
                        )

                entry_offset += 16

            return {
                "current_self_test_operation": {
                    "value": op_value,
                    "string": self._op_value_to_string(op_value),
                },
                "current_self_test_completion": completion,
                "entries": entries,
            }
        except (ValueError, IndexError) as e:
            # Return empty structure on parse error
            return {
                "current_self_test_operation": {
                    "value": 0,
                    "string": f"Parse error: {e}",
                },
                "current_self_test_completion": 0,
                "entries": [],
            }

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

            # Check if test is in progress
            # Value 0 = no test, 1 = short test, 2 = extended test, 0xF = abort
            in_progress = value in (1, 2)  # Only 1 (short) or 2 (extended) means in progress

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

    def _parse_self_test_log(self, log_data: dict) -> dict:
        """
        Parse self-test log page data.

        Per NVMe spec 2.3, Log Page 0x06 structure:
        - Byte 0: Current self-test operation
        - Byte 1: Current self-test completion
        - Bytes 2-3: Reserved
        - Bytes 4-19: Self-test result data structure (entry 1)
        - ... (up to 20 entries)

        :param log_data: Raw log page data from nvme-cli
        :return: Parsed self-test log dictionary
        """
        # nvme-cli returns the log in a specific format
        # The structure may vary, so we handle both raw bytes and parsed JSON

        result = {
            "current_self_test_operation": {
                "value": 0,
                "string": "No self-test in progress",
            },
            "current_self_test_completion": 0,
            "entries": [],
        }

        # If log_data is already parsed by nvme-cli
        if isinstance(log_data, dict):
            # Check for common nvme-cli output formats
            if "dst" in log_data:
                dst = log_data["dst"]
                result["current_self_test_operation"]["value"] = dst.get("dstc", 0)
                result["current_self_test_completion"] = dst.get("dstc", 0)

                # Parse entries if available
                if "entries" in dst:
                    result["entries"] = self._parse_entries(dst["entries"])
            elif "SelfTestLog" in log_data:
                # Alternative format
                stl = log_data["SelfTestLog"]
                result["current_self_test_operation"]["value"] = stl.get("CurrentOperation", 0)
                result["current_self_test_completion"] = stl.get("CurrentCompletion", 0)

                # Parse entries if available
                if "entries" in stl:
                    result["entries"] = self._parse_entries(stl["entries"])
            elif "current_operation" in log_data or "entries" in log_data:
                # Direct format from self-test-log command
                result["current_self_test_operation"]["value"] = log_data.get("current_operation", 0)
                result["current_self_test_completion"] = log_data.get("current_completion", 0)

                # Parse entries if available
                if "entries" in log_data:
                    result["entries"] = self._parse_entries(log_data["entries"])

        # Map operation values to strings
        op_value = result["current_self_test_operation"]["value"]
        result["current_self_test_operation"]["string"] = self._op_value_to_string(op_value)

        return result

    def _parse_self_test_log_text(self, text: str) -> dict:
        """
        Parse text output from 'nvme self-test-log' command.

        Format:
        Device Self Test Log for NVME device:nvme0
        Current operation  : 0
        Current Completion : 0%
        Self Test Result[0]:
          Operation Result             : 0
          Self Test Code               : 1
          ...

        :param text: Text output from self-test-log command
        :return: Parsed dictionary
        """
        result = {
            "current_self_test_operation": {
                "value": 0,
                "string": "No self-test in progress",
            },
            "current_self_test_completion": 0,
            "entries": [],
        }

        import re

        # Parse current operation
        op_match = re.search(r"Current operation\s*:\s*(\d+)", text)
        if op_match:
            op_value = int(op_match.group(1))
            result["current_self_test_operation"]["value"] = op_value
            result["current_self_test_operation"]["string"] = self._op_value_to_string(op_value)

        # Parse completion percentage
        comp_match = re.search(r"Current Completion\s*:\s*(\d+)%", text)
        if comp_match:
            result["current_self_test_completion"] = int(comp_match.group(1))

        # Parse entries (Self Test Result[N]: blocks)
        # Format:
        # Self Test Result[0]:
        #   Operation Result             : 0
        #   Self Test Code               : 1
        #   ...
        # Self Test Result[1]:
        #   ...

        # Find all entry blocks - use MULTILINE and DOTALL for flexible matching
        # Pattern matches: "Self Test Result[N]:" followed by "Operation Result : X" and "Self Test Code : Y"
        entry_pattern = (
            r"Self Test Result\[(\d+)\]:\s*\n\s*Operation Result\s*:\s*(\d+)\s*\n\s*Self Test Code\s*:\s*(\d+)"
        )

        for match in re.finditer(entry_pattern, text, re.MULTILINE | re.DOTALL):
            entry_idx = int(match.group(1))
            result_val = int(match.group(2))
            type_val = int(match.group(3))

            # Only add valid entries (result 0-2, type 1-2)
            if result_val in (0, 1, 2) and type_val in (1, 2):
                result["entries"].append(
                    {
                        "result": result_val,
                        "result_string": self._result_to_string(result_val),
                        "type": type_val,
                        "type_string": self._type_to_string(type_val),
                        "completion_time": 0,  # Would need to parse POH if available
                    }
                )

        return result

    @staticmethod
    def _op_value_to_string(op_value: int) -> str:
        """Convert operation value to string."""
        if op_value == 0:
            return "No self-test in progress"
        elif op_value == 1:
            return "Short self-test in progress"
        elif op_value == 2:
            return "Extended self-test in progress"
        elif op_value == 0xF:
            return "Abort self-test"
        else:
            return f"Unknown operation ({op_value})"

    def _parse_entries(self, entries: list) -> list[dict]:
        """
        Parse self-test result entries.

        Each entry (16 bytes) contains:
        - Byte 0: Self-test result (0=success, 1=fail, 2=aborted)
        - Byte 1: Self-test type (1=short, 2=extended)
        - Bytes 2-7: Reserved
        - Bytes 8-15: Self-test completion timestamp

        :param entries: List of entry data
        :return: List of parsed entry dictionaries
        """
        parsed = []

        for entry in entries:
            if isinstance(entry, dict):
                parsed_entry = {
                    "result": entry.get("result", 0),
                    "result_string": self._result_to_string(entry.get("result", 0)),
                    "type": entry.get("type", 0),
                    "type_string": self._type_to_string(entry.get("type", 0)),
                    "completion_time": entry.get("completion_time", 0),
                }
                parsed.append(parsed_entry)

        return parsed

    @staticmethod
    def _result_to_string(result: int) -> str:
        """Convert result code to string."""
        result_map = {
            0: "Success",
            1: "Failed",
            2: "Aborted",
        }
        return result_map.get(result, f"Unknown ({result})")

    @staticmethod
    def _type_to_string(test_type: int) -> str:
        """Convert test type code to string."""
        type_map = {
            1: "Short",
            2: "Extended",
        }
        return type_map.get(test_type, f"Unknown ({test_type})")

    def get_failed_tests(self, days: int = 90) -> list[dict]:
        """
        Get failed self-tests within specified days.

        :param days: Number of days to look back (default: 90)
        :return: List of failed test entries
        """
        results = self.get_results()
        entries = results.get("entries", [])

        failed = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for entry in entries:
            if entry.get("result", 0) == 1:  # Failed
                # Check if within time window (if timestamp available)
                failed.append(entry)

        return failed

    def has_recent_failures(self, days: int = 90) -> bool:
        """
        Check if device has recent failed self-tests.

        :param days: Number of days to check (default: 90)
        :return: True if failures found
        """
        return len(self.get_failed_tests(days)) > 0

    def get_last_test_date(self) -> datetime | None:
        """
        Get date of last self-test.

        :return: Datetime of last test or None
        """
        results = self.get_results()
        entries = results.get("entries", [])

        if not entries:
            return None

        # Get most recent entry (first in list typically)
        last_entry = entries[0]
        completion_time = last_entry.get("completion_time", 0)

        if completion_time:
            # Convert timestamp to datetime
            # NVMe timestamps are typically in seconds since epoch
            try:
                return datetime.fromtimestamp(completion_time)
            except (ValueError, OSError):
                return None

        return None

    def days_since_last_test(self) -> int | None:
        """
        Get number of days since last self-test.

        :return: Days since last test or None if never tested
        """
        last_test = self.get_last_test_date()
        if last_test is None:
            return None

        delta = datetime.now() - last_test
        return delta.days
