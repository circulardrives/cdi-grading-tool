#
# Copyright (c) 2025 Circular Drive Initiative.
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
Output Validation for CDI Health

Validates device output against expected schema and consistency rules.
"""

from __future__ import annotations

from typing import Any

# Valid CDI grades
VALID_GRADES = {"A", "B", "C", "D", "F", "U"}

# Valid transport protocols
VALID_PROTOCOLS = {"ATA", "NVMe", "SCSI", "USB", "SD", "FusionIO", "Unknown"}

# Valid media types
VALID_MEDIA_TYPES = {"HDD", "SSD", "Not Reported"}

# Required fields for device output
REQUIRED_FIELDS = [
    "dut",
    "transport_protocol",
    "media_type",
    "cdi_grade",
    "cdi_eligible",
    "cdi_certified",
]

# Optional but expected fields
EXPECTED_FIELDS = [
    "vendor",
    "model_number",
    "serial_number",
    "firmware_revision",
    "bytes",
    "smart_supported",
    "smart_enabled",
    "smart_status",
]


class ValidationError:
    """Represents a single validation error."""

    def __init__(self, field: str, message: str, severity: str = "error"):
        """
        Initialize a validation error.

        :param field: Field name where error occurred
        :param message: Error description
        :param severity: "error", "warning", or "info"
        """
        self.field = field
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.field}: {self.message}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
        }


class ValidationResult:
    """Result of validating a device output."""

    def __init__(self, device_id: str = None):
        """
        Initialize validation result.

        :param device_id: Device identifier for reporting
        """
        self.device_id = device_id
        self.errors: list[ValidationError] = []
        self.warnings: list[ValidationError] = []
        self.info: list[ValidationError] = []

    def add_error(self, field: str, message: str) -> None:
        """Add an error."""
        self.errors.append(ValidationError(field, message, "error"))

    def add_warning(self, field: str, message: str) -> None:
        """Add a warning."""
        self.warnings.append(ValidationError(field, message, "warning"))

    def add_info(self, field: str, message: str) -> None:
        """Add an info message."""
        self.info.append(ValidationError(field, message, "info"))

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0

    def __str__(self) -> str:
        lines = []
        if self.device_id:
            lines.append(f"Validation results for {self.device_id}:")
        else:
            lines.append("Validation results:")

        if self.is_valid and not self.has_warnings:
            lines.append("  All checks passed")
        else:
            for error in self.errors:
                lines.append(f"  {error}")
            for warning in self.warnings:
                lines.append(f"  {warning}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "device_id": self.device_id,
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "info": [i.to_dict() for i in self.info],
        }


def validate_device_output(device: dict) -> ValidationResult:
    """
    Validate a single device output dictionary.

    :param device: Device dictionary to validate
    :return: ValidationResult with any issues found
    """
    result = ValidationResult(device.get("dut", "unknown"))

    # Check required fields
    _validate_required_fields(device, result)

    # Check field types
    _validate_field_types(device, result)

    # Check field values
    _validate_field_values(device, result)

    # Check consistency rules
    _validate_consistency(device, result)

    return result


def _validate_required_fields(device: dict, result: ValidationResult) -> None:
    """Validate that required fields are present."""
    for field in REQUIRED_FIELDS:
        if field not in device:
            result.add_error(field, f"Required field '{field}' is missing")
        elif device[field] is None:
            result.add_error(field, f"Required field '{field}' is None")

    # Check expected fields (warnings only)
    for field in EXPECTED_FIELDS:
        if field not in device:
            result.add_warning(field, f"Expected field '{field}' is missing")
        elif device[field] is None:
            result.add_info(field, f"Expected field '{field}' is None")


def _validate_field_types(device: dict, result: ValidationResult) -> None:
    """Validate field types."""
    # String fields
    string_fields = [
        "dut",
        "dut_sg",
        "vendor",
        "model_number",
        "serial_number",
        "firmware_revision",
        "transport_protocol",
        "media_type",
        "cdi_grade",
    ]

    for field in string_fields:
        if field in device and device[field] is not None:
            if not isinstance(device[field], str):
                result.add_error(field, f"Expected string, got {type(device[field]).__name__}")

    # Boolean fields
    bool_fields = [
        "cdi_eligible",
        "cdi_certified",
        "smart_supported",
        "smart_enabled",
        "smart_status",
    ]

    for field in bool_fields:
        if field in device and device[field] is not None:
            if not isinstance(device[field], bool):
                result.add_error(field, f"Expected boolean, got {type(device[field]).__name__}")

    # Numeric fields
    numeric_fields = [
        "bytes",
        "kilobytes",
        "megabytes",
        "gigabytes",
        "terabytes",
        "sectors",
        "logical_sector_size",
        "physical_sector_size",
    ]

    for field in numeric_fields:
        if field in device and device[field] is not None:
            if not isinstance(device[field], (int, float)):
                result.add_error(field, f"Expected number, got {type(device[field]).__name__}")


def _validate_field_values(device: dict, result: ValidationResult) -> None:
    """Validate field values are within expected ranges."""
    # CDI grade
    if "cdi_grade" in device and device["cdi_grade"] is not None:
        if device["cdi_grade"] not in VALID_GRADES:
            result.add_error("cdi_grade", f"Invalid grade '{device['cdi_grade']}', expected one of {VALID_GRADES}")

    # Transport protocol
    if "transport_protocol" in device and device["transport_protocol"] is not None:
        if device["transport_protocol"] not in VALID_PROTOCOLS:
            result.add_warning(
                "transport_protocol",
                f"Unexpected protocol '{device['transport_protocol']}', expected one of {VALID_PROTOCOLS}",
            )

    # Media type
    if "media_type" in device and device["media_type"] is not None:
        if device["media_type"] not in VALID_MEDIA_TYPES:
            result.add_warning(
                "media_type", f"Unexpected media type '{device['media_type']}', expected one of {VALID_MEDIA_TYPES}"
            )

    # Capacity validation (bytes should be positive if set)
    if "bytes" in device and device["bytes"] is not None:
        if device["bytes"] < 0:
            result.add_error("bytes", "Capacity in bytes cannot be negative")
        elif device["bytes"] == 0:
            result.add_warning("bytes", "Capacity is 0 bytes")

    # Sector counts (should be non-negative)
    sector_fields = ["reallocated_sectors", "pending_sectors", "uncorrectable_errors"]
    for field in sector_fields:
        if field in device and device[field] is not None:
            if isinstance(device[field], (int, float)) and device[field] < 0:
                result.add_warning(field, f"{field} is negative ({device[field]})")


def _validate_consistency(device: dict, result: ValidationResult) -> None:
    """Validate consistency between related fields."""
    # Grade vs certified consistency
    grade = device.get("cdi_grade")
    certified = device.get("cdi_certified")
    eligible = device.get("cdi_eligible")

    if grade == "A" and certified is False:
        result.add_warning("cdi_certified", "Grade is 'A' but device is not certified")

    if grade == "F" and certified is True:
        result.add_error("cdi_certified", "Grade is 'F' but device is marked as certified")

    if certified is True and eligible is False:
        result.add_error("cdi_eligible", "Device is certified but not eligible")

    # SMART status vs grade consistency
    smart_status = device.get("smart_status")
    if smart_status is False and grade not in {"F", "U"}:
        result.add_warning("cdi_grade", f"SMART status failed but grade is '{grade}' (expected 'F')")

    # Protocol vs media type consistency
    protocol = device.get("transport_protocol")
    media_type = device.get("media_type")

    if protocol == "NVMe" and media_type == "HDD":
        result.add_warning("media_type", "NVMe devices are typically SSDs, not HDDs")

    # Capacity consistency
    bytes_val = device.get("bytes", 0)
    gigabytes_val = device.get("gigabytes", 0)

    if bytes_val > 0 and gigabytes_val > 0:
        expected_gb = bytes_val / (1000**3)
        if abs(expected_gb - gigabytes_val) > 0.01 * expected_gb:  # 1% tolerance
            result.add_warning("gigabytes", f"Gigabytes ({gigabytes_val}) inconsistent with bytes ({bytes_val})")


def validate_devices_output(devices: list[dict]) -> list[ValidationResult]:
    """
    Validate a list of device outputs.

    :param devices: List of device dictionaries
    :return: List of ValidationResults
    """
    results = []

    if not isinstance(devices, list):
        result = ValidationResult()
        result.add_error("devices", f"Expected list, got {type(devices).__name__}")
        return [result]

    for i, device in enumerate(devices):
        if not isinstance(device, dict):
            result = ValidationResult(f"device[{i}]")
            result.add_error("device", f"Expected dict, got {type(device).__name__}")
            results.append(result)
        else:
            results.append(validate_device_output(device))

    return results


def format_validation_report(results: list[ValidationResult], verbose: bool = False) -> str:
    """
    Format validation results as a human-readable report.

    :param results: List of ValidationResults
    :param verbose: Include info-level messages
    :return: Formatted report string
    """
    lines = ["=" * 60, "CDI Health Output Validation Report", "=" * 60, ""]

    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    valid_count = sum(1 for r in results if r.is_valid)

    lines.append(f"Devices validated: {len(results)}")
    lines.append(f"Passed: {valid_count}")
    lines.append(f"Failed: {len(results) - valid_count}")
    lines.append(f"Total errors: {total_errors}")
    lines.append(f"Total warnings: {total_warnings}")
    lines.append("")

    for result in results:
        if not result.is_valid or result.has_warnings or verbose:
            lines.append("-" * 40)
            lines.append(str(result))

            if verbose and result.info:
                for info in result.info:
                    lines.append(f"  {info}")

    lines.append("")
    lines.append("=" * 60)

    if total_errors == 0 and total_warnings == 0:
        lines.append("All validations passed!")
    elif total_errors == 0:
        lines.append(f"Validation passed with {total_warnings} warning(s)")
    else:
        lines.append(f"Validation FAILED with {total_errors} error(s)")

    lines.append("=" * 60)

    return "\n".join(lines)
