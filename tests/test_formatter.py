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
