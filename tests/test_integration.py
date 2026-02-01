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

"""Integration tests for CDI Health."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cdi_health.classes.formatter import get_formatter
from cdi_health.classes.scoring import HealthScoreCalculator


@pytest.mark.integration
class TestIntegration:
    """Integration tests."""

    def test_end_to_end_scan_mock_data(self, mock_data_dir: Path) -> None:
        """Test end-to-end scan with mock data."""
        from cdi_health.cli import scan_devices_mock
        
        devices = scan_devices_mock(str(mock_data_dir))
        assert isinstance(devices, list)
        
        # Skip if no devices found (may happen if mock data structure changed)
        if not devices:
            pytest.skip("No mock devices available - mock data structure may have changed")
        
        # Test scoring
        calculator = HealthScoreCalculator()
        for device in devices:
            score = calculator.calculate(device)
            assert score.score >= 0
            assert score.score <= 100
            assert score.grade in ("A", "B", "C", "D", "F")
            assert score.status in ("Excellent", "Good", "Fair", "Poor", "Failed")

    def test_formatter_with_scored_devices(self, mock_data_dir: Path) -> None:
        """Test formatters with scored devices."""
        from cdi_health.cli import scan_devices_mock
        from cdi_health.classes.scoring import HealthScoreCalculator
        
        devices = scan_devices_mock(str(mock_data_dir))
        
        # Skip if no devices found
        if not devices:
            pytest.skip("No mock devices available for testing")
        
        calculator = HealthScoreCalculator()
        
        # Score devices
        scored_devices = []
        for device in devices:
            score = calculator.calculate(device)
            device.update(score.to_dict())
            scored_devices.append(device)
        
        # Test all formatters
        for fmt_name in ["table", "json", "csv", "yaml"]:
            formatter = get_formatter(fmt_name)
            result = formatter.format(scored_devices)
            assert isinstance(result, str)
            # Some formatters may return empty for empty input, but we have devices
            if scored_devices:
                assert len(result) > 0

    def test_mock_data_files_exist(self, mock_data_dir: Path) -> None:
        """Test that mock data files exist and are valid JSON."""
        import json
        
        # Check NVMe devices
        nvme_dir = mock_data_dir / "nvme"
        if nvme_dir.exists():
            nvme_files = list(nvme_dir.glob("*.json"))
            assert len(nvme_files) > 0, "No NVMe mock data files found"
            
            for file in nvme_files:
                with file.open() as f:
                    data = json.load(f)
                    assert isinstance(data, dict)
        
        # Check ATA devices
        ata_dir = mock_data_dir / "ata"
        if ata_dir.exists():
            ata_files = list(ata_dir.glob("*.json"))
            assert len(ata_files) > 0, "No ATA mock data files found"
            
            for file in ata_files:
                with file.open() as f:
                    data = json.load(f)
                    assert isinstance(data, dict)
