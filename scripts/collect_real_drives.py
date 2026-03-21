#!/usr/bin/env python3
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
Script to collect real drive data and anonymize serial numbers for mock data.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def anonymize_serial(serial: str, index: int) -> str:
    """Anonymize serial number while keeping format."""
    if not serial or serial == "Not Reported":
        return f"MOCK{index:06d}"

    # Keep first 2-3 chars if they're letters, replace rest with numbers
    match = re.match(r"^([A-Z]{2,3})(.*)$", serial.upper())
    if match:
        prefix = match.group(1)
        suffix = match.group(2)
        # Replace suffix with index-based numbers
        new_suffix = f"{index:06d}"[: len(suffix)] if suffix else f"{index:06d}"
        return f"{prefix}{new_suffix}"

    # If no pattern match, use generic format
    return f"MOCK{index:06d}"


def anonymize_wwn(wwn_data: dict | None, index: int) -> dict | None:
    """Anonymize WWN data."""
    if not wwn_data:
        return None

    if isinstance(wwn_data, dict):
        # Keep structure but change ID
        return {"naa": wwn_data.get("naa", 5), "oui": wwn_data.get("oui", 3152), "id": 100000000000 + index}
    return wwn_data


def anonymize_json(data: dict, index: int, original_serial: str = None) -> dict:
    """Anonymize sensitive data in JSON."""
    data = json.loads(json.dumps(data))  # Deep copy

    # Get original serial if not provided
    if original_serial is None:
        original_serial = data.get("serial_number", "")

    # Generate anonymized serial
    anonymized_serial = anonymize_serial(original_serial, index) if original_serial else f"MOCK{index:06d}"

    # Anonymize serial_number (can be at top level or in device info)
    if "serial_number" in data:
        data["serial_number"] = anonymized_serial

    # Also check in device section
    if "device" in data and isinstance(data["device"], dict):
        if "serial_number" in data["device"]:
            data["device"]["serial_number"] = anonymized_serial

    # Anonymize in output text (smartctl output often contains serial numbers)
    if "smartctl" in data and isinstance(data["smartctl"], dict):
        if "output" in data["smartctl"] and isinstance(data["smartctl"]["output"], list):
            for i, line in enumerate(data["smartctl"]["output"]):
                if original_serial and original_serial in line:
                    # Replace serial number in output text
                    data["smartctl"]["output"][i] = line.replace(original_serial, anonymized_serial)

    # Anonymize WWN
    if "wwn" in data:
        if isinstance(data["wwn"], dict):
            data["wwn"] = anonymize_wwn(data["wwn"], index)
        elif isinstance(data["wwn"], str) and data["wwn"] != "Not Reported":
            data["wwn"] = f"0x{5000000000000000 + index:016x}"

    # Anonymize in device name (keep structure but anonymize)
    if "device" in data and isinstance(data["device"], dict):
        if "name" in data["device"]:
            # Keep device name format but anonymize if it contains serial-like patterns
            device_name = data["device"]["name"]
            # Replace /dev/sdX with /dev/sdX (keep structure)
            pass

    # Anonymize in smart_attributes if present (some may contain serials)
    if "smart_attributes" in data:
        for attr in data["smart_attributes"]:
            if "raw" in attr and isinstance(attr["raw"], dict):
                raw_str = attr["raw"].get("string", "")
                # Check if raw value might contain serial-like data
                if original_serial and original_serial in raw_str:
                    attr["raw"]["string"] = raw_str.replace(original_serial, anonymized_serial)

    return data


def get_smartctl_json(device: str) -> dict | None:
    """Get raw smartctl JSON output for a device."""
    # Try without sudo first, then with sudo
    # Note: smartctl may return non-zero exit code but still produce valid JSON
    for cmd in [
        ["smartctl", "--xall", "--json=ov", device],
        ["sudo", "smartctl", "--xall", "--json=ov", device],
    ]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # Don't fail on non-zero exit, smartctl uses it for warnings
            )
            # Try to parse JSON even if exit code is non-zero
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    # Check if we got valid data (not just an error message)
                    if "json_format_version" in data:
                        # Check for error messages
                        if "messages" in data.get("smartctl", {}):
                            messages = data["smartctl"].get("messages", [])
                            errors = [m for m in messages if m.get("severity") == "error"]
                            if errors:
                                # Has errors, try next command
                                continue
                        # Check if we have device data
                        if "device" in data or "serial_number" in data:
                            return data
                except json.JSONDecodeError:
                    # Not valid JSON, try next command
                    continue
        except FileNotFoundError:
            # Command not found, try next
            continue

    return None


def main():
    """Main function."""
    # Get list of devices from cdi-health scan
    print("Scanning devices...")
    result = subprocess.run(["cdi-health", "scan", "-o", "json"], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error scanning devices: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    devices = json.loads(result.stdout)
    print(f"Found {len(devices)} devices\n")

    # Determine output directory
    mock_data_dir = Path(__file__).parent.parent / "src" / "cdi_health" / "mock_data"

    # Group devices by transport protocol
    devices_by_protocol = {}
    for i, device in enumerate(devices):
        protocol = device.get("transport_protocol", "unknown").lower()
        if protocol not in devices_by_protocol:
            devices_by_protocol[protocol] = []
        devices_by_protocol[protocol].append((i, device))

    # Process each device
    for protocol, device_list in devices_by_protocol.items():
        protocol_dir = mock_data_dir / protocol
        protocol_dir.mkdir(parents=True, exist_ok=True)

        for index, device_info in device_list:
            device_path = device_info["dut"]
            model = device_info.get("model_number", "Unknown")
            serial = device_info.get("serial_number", "Unknown")

            print(f"Processing {device_path} ({protocol.upper()}): {model} - {serial}")

            # Get raw smartctl JSON
            smartctl_data = get_smartctl_json(device_path)
            if not smartctl_data:
                print(f"  ⚠ Skipping {device_path} (could not get smartctl data)")
                continue

            # Anonymize the data
            original_serial = device_info.get("serial_number", "")
            anonymized = anonymize_json(smartctl_data, index, original_serial)

            # Create filename based on model and health status
            health_status = "healthy"
            if not device_info.get("smart_status", True):
                health_status = "failing_smart"
            elif device_info.get("health_grade") == "F":
                health_status = "failing"
            elif (device_info.get("reallocated_sectors") or 0) > 10:
                health_status = "high_reallocated"
            elif (device_info.get("pending_sectors") or 0) > 10:
                health_status = "high_pending"
            elif (device_info.get("uncorrectable_errors") or 0) > 10:
                health_status = "high_uncorrectable"

            # Create safe filename from model
            safe_model = re.sub(r"[^a-zA-Z0-9]", "_", model)[:30]
            filename = f"{safe_model}_{health_status}.json"
            filepath = protocol_dir / filename

            # If file exists, add index
            if filepath.exists():
                filename = f"{safe_model}_{index}_{health_status}.json"
                filepath = protocol_dir / filename

            # Write anonymized data
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(anonymized, f, indent=2)

            print(f"  ✓ Saved to {filepath.relative_to(mock_data_dir.parent.parent)}")
            print(f"    Anonymized serial: {anonymized.get('serial_number', 'N/A')}")

    print(f"\n✓ Done! Mock data saved to {mock_data_dir}")


if __name__ == "__main__":
    main()
