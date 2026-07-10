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

"""Unit tests for Device / Devices / protocol parsers."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cdi_health.classes.devices import ATAProtocol, Device, Devices
from cdi_health.classes.exceptions import CommandException
from cdi_health.classes.mock import MockSG3Utils, MockSmartctl, create_mock_device
from cdi_health.classes.scoring import HealthScoreCalculator


@pytest.fixture
def mock_data_dir() -> Path:
    return Path(__file__).parent.parent / "src" / "cdi_health" / "mock_data"


def _load_mock(mock_data_dir: Path, *parts: str) -> dict:
    with (mock_data_dir.joinpath(*parts)).open() as f:
        return json.load(f)


def _device_from_mock(mock_data: dict, *, sg3: MockSG3Utils | None = None) -> Device:
    device_id = mock_data.get("device", {}).get("name", "/dev/mock0")
    smartctl = MockSmartctl(device_id=device_id, mock_data=mock_data)
    sg = sg3 or MockSG3Utils(device_id=device_id)
    return Device(device_id=device_id, smartctl_provider=smartctl, sg3utils_provider=sg)


class TestDeviceReady:
    """is_ready / are_ready (#73)."""

    def test_is_ready_uses_state(self, mock_data_dir: Path) -> None:
        data = _load_mock(mock_data_dir, "ata", "healthy_hdd.json")
        device = _device_from_mock(data)
        assert device.state == "Ready"
        assert device.is_ready is True

        device.state = "Not Ready"
        assert device.is_ready is False

    def test_are_ready_all_dicts(self) -> None:
        devices = Devices.__new__(Devices)
        devices.devices = [{"state": "Ready"}, {"state": "Ready"}]
        assert devices.are_ready is True

        devices.devices = [{"state": "Ready"}, {"state": "Not Ready"}]
        assert devices.are_ready is False

    def test_are_ready_empty(self) -> None:
        devices = Devices.__new__(Devices)
        devices.devices = []
        assert devices.are_ready is True


class TestGetSmartAttributeById:
    """Selector modes for get_smart_attribute_by_id (#81)."""

    SAMPLE = [
        {
            "id": 5,
            "value": 100,
            "worst": 99,
            "threshold": 10,
            "flags": {"value": 1, "string": "POSR--"},
            "raw": {"value": 42, "string": "42"},
        }
    ]

    def test_raw_default(self) -> None:
        assert ATAProtocol.get_smart_attribute_by_id(self.SAMPLE, attribute_id=5) == 42

    def test_actual_value(self) -> None:
        assert ATAProtocol.get_smart_attribute_by_id(self.SAMPLE, attribute_id=5, actual_value=True) == 100

    def test_worst_value(self) -> None:
        assert ATAProtocol.get_smart_attribute_by_id(self.SAMPLE, attribute_id=5, worst_value=True) == 99

    def test_threshold(self) -> None:
        assert ATAProtocol.get_smart_attribute_by_id(self.SAMPLE, attribute_id=5, threshold=True) == 10

    def test_flags(self) -> None:
        flags = ATAProtocol.get_smart_attribute_by_id(self.SAMPLE, attribute_id=5, flags=True)
        assert flags == {"value": 1, "string": "POSR--"}

    def test_missing_returns_default(self) -> None:
        assert ATAProtocol.get_smart_attribute_by_id(self.SAMPLE, attribute_id=999, default=-1) == -1


class TestATAProtocol:
    def test_healthy_hdd(self, mock_data_dir: Path) -> None:
        data = _load_mock(mock_data_dir, "ata", "healthy_hdd.json")
        device = _device_from_mock(data)
        assert device.transport_protocol == "ATA"
        assert device.media_type == "HDD"
        assert device.smart_status is True
        assert device.pending_sectors == 0
        assert device.uncorrectable_errors == 0
        assert device.pending_reallocated_sectors == device.pending_sectors
        assert device.offline_uncorrectable_sectors == device.uncorrectable_errors
        assert device.cdi_grade in {"A", "B", "C", "D", "F"}

    def test_ata_ssd_without_rotation_rate_classifies_ssd(self, mock_data_dir: Path) -> None:
        data = _load_mock(mock_data_dir, "ata", "SDSSDH3_512G_healthy.json")
        data = copy.deepcopy(data)
        data.pop("rotation_rate", None)
        device = _device_from_mock(data)
        assert device.media_type == "SSD"
        assert device.transport_protocol == "ATA"


class TestNVMeProtocol:
    def test_health_log_maps_temperature(self, mock_data_dir: Path) -> None:
        data = _load_mock(mock_data_dir, "nvme", "KCD81VUG6T40_healthy.json")
        device = _device_from_mock(data)
        assert device.transport_protocol == "NVMe"
        expected = data["nvme_smart_health_information_log"]["temperature"]
        assert device.current_temperature == expected
        assert device.percentage_used == data["nvme_smart_health_information_log"]["percentage_used"]
        assert isinstance(device.smart_status, bool)


class TestSCSIProtocol:
    def test_error_counter_log(self, mock_data_dir: Path) -> None:
        data = _load_mock(mock_data_dir, "scsi", "healthy_sas.json")
        device = _device_from_mock(data)
        assert device.transport_protocol == "SCSI"
        assert device.uncorrectable_errors == 0
        assert device.offline_uncorrectable_sectors == 0
        assert device.reallocated_sectors == 0  # grown defects


class TestDeviceErrorPaths:
    def test_malformed_smartctl_json_raises(self) -> None:
        smartctl = MagicMock()
        smartctl.get_all_as_json.side_effect = CommandException("Failed to parse smartctl JSON")
        sg = MockSG3Utils(device_id="/dev/sda")
        with pytest.raises(CommandException, match="Failed to parse"):
            Device(device_id="/dev/sda", smartctl_provider=smartctl, sg3utils_provider=sg)

    def test_sg_map26_false_falls_back_to_block_path(self, mock_data_dir: Path) -> None:
        data = _load_mock(mock_data_dir, "ata", "healthy_hdd.json")
        device_id = data["device"]["name"]

        class FailingMapSG(MockSG3Utils):
            def sg_map26(self):
                return False

        sg = FailingMapSG(device_id=device_id)
        smartctl = MockSmartctl(device_id=device_id, mock_data=data)
        device = Device(device_id=device_id, smartctl_provider=smartctl, sg3utils_provider=sg)
        assert device.dut_sg == device_id


class TestCreateMockDeviceHelper:
    def test_create_mock_device_ata(self, mock_data_dir: Path) -> None:
        device = create_mock_device(json_file=mock_data_dir / "ata" / "healthy_hdd.json")
        assert device.media_type == "HDD"
        assert device.is_ready is True


class TestATASelfTestScoring:
    def test_failed_ata_selftest_is_grade_f(self) -> None:
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "ATA",
            "media_type": "HDD",
            "smart_status": True,
            "smart_self_tests": [
                {
                    "type": {"value": 1, "string": "Short offline"},
                    "status": {"value": 7, "string": "Completed: read failure", "passed": False},
                    "lifetime_hours": 100,
                }
            ],
        }
        result = calculator.calculate(device)
        assert result.grade == "F"
        assert result.score == 0
        assert any("self-test" in d.reason.lower() for d in result.deductions)

    def test_passed_ata_selftest_no_deduction(self) -> None:
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "ATA",
            "media_type": "HDD",
            "smart_status": True,
            "smart_self_tests": [
                {
                    "status": {"value": 0, "string": "Completed without error", "passed": True},
                }
            ],
        }
        result = calculator.calculate(device)
        assert result.grade == "A"
        assert not any("self-test" in d.reason.lower() for d in result.deductions)
