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

"""Tests for Revert Standard §13/§15 output schema and UNGRADED failure emission."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from cdi_health.classes.devices import Devices
from cdi_health.classes.formatter import CSVFormatter, JSONFormatter
from cdi_health.classes.reporter import ReportGenerator
from cdi_health.classes.revert import (
    FLAG_DUPLICATE_SERIAL,
    FLAG_SMART_RESET_SUSPECTED,
    REVERT_STANDARD_VERSION,
    STATUS_UNGRADED,
    UNGRADED_DEVICE_OPEN_FAILURE,
    UNGRADED_DEVICE_TIMEOUT,
    UNGRADED_RAID_PASSTHROUGH,
    flag_duplicate_serials,
    revert_fields,
    warning_flags,
)


def _healthy_ata() -> dict:
    return {
        "dut": "/dev/sda",
        "serial_number": "HEALTHY001",
        "model_number": "MOCK-HDD",
        "vendor": "MOCK",
        "transport_protocol": "ATA",
        "media_type": "HDD",
        "smart_status": True,
        "state": "Ready",
        "power_on_hours": 1000,
        "power_cycle_count": 50,
        "reallocated_sectors": 0,
        "pending_sectors": 0,
        "uncorrectable_errors": 0,
        "current_temperature": 35,
        "maximum_temperature": 60,
        "grading_status": "GRADED",
        "ungraded_reasons": [],
        "warning_flags": [],
        "smart_data_readable": True,
        "security_locked": False,
        "scan_timestamp": "2026-08-06T12:00:00+00:00",
    }


class TestUngradedPlaceholder:
    """devices.failures → UNGRADED placeholder rows (#117 / #122)."""

    def test_open_error_becomes_device_open_failure(self) -> None:
        row = Devices._ungraded_placeholder(
            {
                "name": "/dev/sdb",
                "protocol": "SCSI",
                "open_error": "Permission denied",
                "serial_number": "ZL23ENM8",
            }
        )
        assert row["grading_status"] == STATUS_UNGRADED
        assert row["serial_number"] == "ZL23ENM8"
        assert row["dut"] == "/dev/sdb"
        assert UNGRADED_DEVICE_OPEN_FAILURE in row["ungraded_reasons"]
        assert "Permission denied" in row["ungraded_detail"]

    def test_timeout_reason_code(self) -> None:
        row = Devices._ungraded_placeholder(
            {"name": "/dev/sdc", "error": "Command timed out after 120s: smartctl -a /dev/sdc"}
        )
        assert UNGRADED_DEVICE_TIMEOUT in row["ungraded_reasons"]

    def test_raid_passthrough_reason(self) -> None:
        row = Devices._ungraded_placeholder(
            {
                "name": "/dev/bus/0",
                "type": "megaraid,0",
                "error": "RAID controller passthrough not supported",
            }
        )
        assert UNGRADED_RAID_PASSTHROUGH in row["ungraded_reasons"]

    def test_analyse_devices_merges_failures(self) -> None:
        devices = Devices.__new__(Devices)
        devices.scanned = []
        devices.failures = [{"name": "/dev/sdz", "open_error": "Device open failed", "serial_number": "ZL23ENM8"}]
        devices.devices = []
        # Skip ThreadPoolExecutor path: empty scanned list, then merge failures.
        devices.analyse_devices()
        assert len(devices.devices) == 1
        assert devices.devices[0]["serial_number"] == "ZL23ENM8"
        assert devices.devices[0]["grading_status"] == STATUS_UNGRADED


class TestRevertSchemaFields:
    """§13 fields present in JSON/CSV enrichment (#120)."""

    EXPECTED_KEYS = {
        "attribute_grades",
        "defect_grade",
        "age_cap_grade",
        "multi_factor_applied",
        "fail_reason_codes",
        "revert_eligible",
        "revert_certified",
        "recommended_use",
        "drive_class",
        "scan_timestamp",
        "revert_standard_version",
        "grading_status",
        "warning_flags",
        "final_grade",
        "ungraded_reasons",
    }

    def test_json_includes_section_13_fields(self) -> None:
        data = json.loads(JSONFormatter().format([_healthy_ata()]))
        assert len(data) == 1
        row = data[0]
        missing = self.EXPECTED_KEYS - set(row)
        assert not missing, f"missing keys: {missing}"
        assert row["revert_standard_version"] == REVERT_STANDARD_VERSION
        assert row["grading_status"] == "GRADED"
        assert row["revert_certified"] in ("true", "Advisory", "false")
        assert row["drive_class"] in ("consumer", "enterprise")
        assert isinstance(row["attribute_grades"], dict)
        assert row["final_grade"] in ("A", "B", "C", "D", "F")

    def test_csv_includes_section_13_headers_and_values(self) -> None:
        text = CSVFormatter().format([_healthy_ata()])
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 1
        for key in (
            "grading_status",
            "fail_reason_codes",
            "attribute_grades",
            "age_cap_grade",
            "defect_grade",
            "multi_factor_applied",
            "revert_eligible",
            "revert_certified",
            "recommended_use",
            "drive_class",
            "scan_timestamp",
            "revert_standard_version",
            "warning_flags",
        ):
            assert key in reader.fieldnames
            assert key in rows[0]

    def test_json_emits_failures_as_ungraded(self) -> None:
        failure = Devices._ungraded_placeholder(
            {
                "name": "/dev/sdb",
                "open_error": "No such device",
                "serial_number": "ZL23ENM8",
                "protocol": "SCSI",
            }
        )
        data = json.loads(JSONFormatter().format([_healthy_ata(), failure]))
        ungraded = [d for d in data if d.get("grading_status") == STATUS_UNGRADED]
        assert len(ungraded) == 1
        row = ungraded[0]
        assert row["serial_number"] == "ZL23ENM8"
        assert row["final_grade"] == "UNGRADED"
        assert row["health_grade"] == "UNGRADED"
        assert row["health_score"] is None
        assert UNGRADED_DEVICE_OPEN_FAILURE in row["ungraded_reasons"]
        assert UNGRADED_DEVICE_OPEN_FAILURE in row["fail_reason_codes"]
        assert row["revert_eligible"] is False
        assert row["revert_certified"] == "false"
        assert row["recommended_use"] == "Manual review required"


class TestWarningFlagsAndDuplicates:
    """§15 warning flags and repeat-serial detection."""

    def test_smart_reset_suspected(self) -> None:
        device = {
            "power_on_hours": 12,
            "power_cycle_count": 250,
            "reallocated_sectors": 0,
            "grown_defects": 0,
            "pending_sectors": 0,
            "uncorrectable_errors": 0,
            "warning_flags": [],
        }
        assert FLAG_SMART_RESET_SUSPECTED in warning_flags(device)

    def test_duplicate_serial_flagged(self) -> None:
        a = _healthy_ata()
        b = _healthy_ata()
        b["dut"] = "/dev/sdb"
        flag_duplicate_serials([a, b])
        assert FLAG_DUPLICATE_SERIAL in a["warning_flags"]
        assert FLAG_DUPLICATE_SERIAL in b["warning_flags"]

        enriched = json.loads(JSONFormatter().format([a, b]))
        assert all(FLAG_DUPLICATE_SERIAL in d["warning_flags"] for d in enriched)


class TestReporterUngradedEmission:
    """HTML/CSV reporter surfaces failures as UNGRADED (#117/#122)."""

    def test_html_includes_ungraded_row(self, tmp_path: Path) -> None:
        failure = Devices._ungraded_placeholder(
            {
                "name": "/dev/sdb",
                "open_error": "Device open failed",
                "serial_number": "ZL23ENM8",
            }
        )
        out = tmp_path / "report.html"
        ReportGenerator().generate_html([_healthy_ata(), failure], str(out))
        html_text = out.read_text(encoding="utf-8")
        assert "ZL23ENM8" in html_text
        assert "UNGRADED" in html_text
        assert "DEVICE_OPEN_FAILURE" in html_text or "Ungraded" in html_text

    def test_reporter_csv_includes_ungraded_and_schema_columns(self, tmp_path: Path) -> None:
        failure = Devices._ungraded_placeholder(
            {
                "name": "/dev/sdb",
                "error": "Command timed out after 120s: smartctl",
                "serial_number": "TIMEOUT01",
            }
        )
        out = tmp_path / "fleet.csv"
        ReportGenerator().generate_csv([_healthy_ata(), failure], str(out))
        text = out.read_text(encoding="utf-8-sig")
        assert "TIMEOUT01" in text
        assert "Grading status" in text
        assert "Fail reason codes" in text
        assert "Revert certified" in text
        assert "Warning flags" in text
        assert "DEVICE_TIMEOUT" in text or "UNGRADED" in text


class TestNaRenderingConsistency:
    """#126: SCSI verify-log not-applicable cells use the report em dash."""

    def test_format_nested_cell_normalizes_not_applicable(self) -> None:
        assert ReportGenerator._format_nested_cell(None) == "—"
        assert ReportGenerator._format_nested_cell("not applicable") == "—"
        assert ReportGenerator._format_nested_cell("N/A") == "—"
        assert ReportGenerator._format_nested_cell("") == "—"

    def test_scsi_missing_verify_section_is_em_dash(self) -> None:
        device = {
            "transport_protocol": "SCSI",
            "smart_attributes": {
                "read": {"total_uncorrected_errors": 0},
                "write": {"total_uncorrected_errors": 0},
                # verify section absent → not applicable for this drive
            },
        }
        cell = ReportGenerator._scsi_error_counter_cell(device, "verify.total_uncorrected_errors")
        assert cell == "—"

    def test_normalize_display_value_not_applicable(self) -> None:
        text, variant = ReportGenerator._normalize_display_value("not applicable")
        assert text == "—"
        assert variant == "is-missing"


class TestRevertFieldsHelpers:
    def test_ungraded_overrides_letter_grade(self) -> None:
        device = {
            "grading_status": STATUS_UNGRADED,
            "ungraded_reasons": ["SECURITY_LOCKED"],
            "health_grade": "A",
            "warning_flags": [],
            "scan_timestamp": "2026-08-06T12:00:00+00:00",
        }
        fields = revert_fields(device, score=None)
        assert fields["final_grade"] == "UNGRADED"
        assert fields["health_grade"] == "UNGRADED"
        assert fields["grading_status"] == STATUS_UNGRADED
        assert fields["fail_reason_codes"] == ["SECURITY_LOCKED"]
        assert fields["age_cap_grade"] is None
        assert fields["defect_grade"] is None
