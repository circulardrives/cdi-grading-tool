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
from cdi_health.classes.revert import (
    FLAG_MISSING_DEFECT_DATA,
    FLAG_POH_NOT_REPORTED,
    FLAG_SMART_RESET_SUSPECTED,
    FLAG_TUR_NOT_READY,
    FLAG_TUR_UNAVAILABLE,
    fail_reason_codes,
    missing_defect_data,
    warning_flags,
)
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

    def test_parses_composite_temp_thresholds_from_smartctl_output(self, mock_data_dir: Path) -> None:
        """NVMe WCTEMP/CCTEMP from smartctl text must drive scoring, not YAML 60 °C."""
        data = _load_mock(mock_data_dir, "nvme", "SSDPEK1A118GA_healthy.json")
        device = _device_from_mock(data)
        assert device.warning_temperature == 70
        assert device.maximum_temperature == 78
        assert device.warning_temp_time == 1
        assert device.critical_comp_time == 0
        # Drive at 61 °C is below manufacturer WCTEMP — must not Grade F.
        # WCTT=1 yields a warning deduction only.
        device.current_temperature = 61
        device.apply_health_grade()
        assert device.cdi_grade == "A"


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
        from cdi_health.classes.config import ThresholdConfig

        ThresholdConfig.reset_instance()
        ThresholdConfig.get_instance().set_grading_profile("binary")
        try:
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
        finally:
            ThresholdConfig.reset_instance()

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


class _StaticTurSG(MockSG3Utils):
    """MockSG3Utils returning a fixed TUR state."""

    tur_state = "Ready"

    def test_unit_ready(self) -> str:
        return self.tur_state


def _sg_with_state(device_id: str, state: str | None) -> MockSG3Utils:
    sg = _StaticTurSG(device_id=device_id)
    sg.tur_state = state
    return sg


class TestTurStateGrading:
    """TUR Unknown / ATA-NVMe Not Ready must not auto-fail drives (#128)."""

    @pytest.mark.parametrize(
        "rel",
        [("ata", "healthy_hdd.json"), ("nvme", "SSDPE2KE032T8_healthy.json"), ("scsi", "healthy_sas.json")],
    )
    def test_unknown_tur_does_not_fail(self, mock_data_dir: Path, rel: tuple[str, str]) -> None:
        data = _load_mock(mock_data_dir, *rel)
        device_id = data.get("device", {}).get("name", "/dev/mock0")
        device = _device_from_mock(data, sg3=_sg_with_state(device_id, "Unknown"))
        assert device.state == "Unknown"
        assert device.cdi_grade != "F"
        d = device.to_dict(pop=True)
        result = HealthScoreCalculator().calculate(d)
        assert not any(x.field == "state" for x in result.deductions)
        assert FLAG_TUR_UNAVAILABLE in warning_flags(d)

    def test_provider_returning_none_is_unknown(self, mock_data_dir: Path) -> None:
        data = _load_mock(mock_data_dir, "ata", "healthy_hdd.json")
        device = _device_from_mock(data, sg3=_sg_with_state(data["device"]["name"], None))
        assert device.state == "Unknown"

    @pytest.mark.parametrize("rel", [("ata", "healthy_hdd.json"), ("nvme", "SSDPE2KE032T8_healthy.json")])
    def test_ata_nvme_not_ready_with_valid_smart_is_waived(self, mock_data_dir: Path, rel: tuple[str, str]) -> None:
        data = _load_mock(mock_data_dir, *rel)
        device_id = data.get("device", {}).get("name", "/dev/mock0")
        device = _device_from_mock(data, sg3=_sg_with_state(device_id, "Not Ready"))
        assert device.state == "Not Ready"
        assert device.cdi_grade != "F"
        d = device.to_dict(pop=True)
        result = HealthScoreCalculator().calculate(d)
        assert "F-NO-RESPONSE" not in fail_reason_codes(result.deductions)
        assert FLAG_TUR_NOT_READY in warning_flags(d)

    def test_scsi_genuine_not_ready_still_fails(self, mock_data_dir: Path) -> None:
        data = _load_mock(mock_data_dir, "scsi", "healthy_sas.json")
        device_id = data.get("device", {}).get("name", "/dev/mock0")
        device = _device_from_mock(data, sg3=_sg_with_state(device_id, "Not Ready"))
        assert device.cdi_grade == "F"
        result = HealthScoreCalculator().calculate(device.to_dict(pop=True))
        assert "F-NO-RESPONSE" in fail_reason_codes(result.deductions)


class TestPowerOnHoursUnknown:
    """POH is never faked to 0 (#129)."""

    @pytest.mark.parametrize("rel", [("ata", "healthy_hdd.json"), ("nvme", "SSDPE2KE032T8_healthy.json")])
    def test_not_ready_keeps_real_poh(self, mock_data_dir: Path, rel: tuple[str, str]) -> None:
        data = _load_mock(mock_data_dir, *rel)
        expected = data["power_on_time"]["hours"]
        assert expected > 0
        device_id = data.get("device", {}).get("name", "/dev/mock0")
        device = _device_from_mock(data, sg3=_sg_with_state(device_id, "Not Ready"))
        assert device.power_on_hours == expected

    @pytest.mark.parametrize(
        "rel",
        [("ata", "healthy_hdd.json"), ("nvme", "SSDPE2KE032T8_healthy.json"), ("scsi", "healthy_sas.json")],
    )
    @pytest.mark.parametrize("state", ["Ready", "Not Ready", "Unknown"])
    def test_missing_poh_is_not_reported_not_zero(self, mock_data_dir: Path, rel: tuple[str, str], state: str) -> None:
        data = copy.deepcopy(_load_mock(mock_data_dir, *rel))
        data.pop("power_on_time", None)
        device_id = data.get("device", {}).get("name", "/dev/mock0")
        device = _device_from_mock(data, sg3=_sg_with_state(device_id, state))
        assert device.power_on_hours == "Not Reported"
        d = device.to_dict(pop=True)
        flags = warning_flags(d)
        assert FLAG_POH_NOT_REPORTED in flags
        assert FLAG_SMART_RESET_SUSPECTED not in flags

    def test_unknown_poh_with_many_power_cycles_is_not_smart_reset(self) -> None:
        # Previously POH forced to "0" + power cycles >= 100 tripped §15.1.
        device = {"transport_protocol": "ATA", "power_on_hours": "Not Reported", "power_cycle_count": 5000}
        flags = warning_flags(device)
        assert FLAG_SMART_RESET_SUSPECTED not in flags
        assert FLAG_POH_NOT_REPORTED in flags

    def test_not_ready_ata_high_poh_still_age_capped(self, mock_data_dir: Path) -> None:
        # A fake 0 used to defeat the §5 age cap; the real POH must drive it.
        data = copy.deepcopy(_load_mock(mock_data_dir, "ata", "healthy_hdd.json"))
        data["power_on_time"] = {"hours": 65000}
        device_id = data["device"]["name"]
        device = _device_from_mock(data, sg3=_sg_with_state(device_id, "Not Ready"))
        result = HealthScoreCalculator().calculate(device.to_dict(pop=True))
        assert device.power_on_hours == 65000
        assert result.age_cap_grade == "D"

    def test_ungraded_failure_record_not_flagged(self) -> None:
        record = Devices._ungraded_placeholder({"name": "/dev/sdz", "error": "open failed"})
        assert FLAG_POH_NOT_REPORTED not in warning_flags(record)


def _drop_ata_attrs(data: dict, *ids: int) -> dict:
    data = copy.deepcopy(data)
    table = data["ata_smart_attributes"]["table"]
    data["ata_smart_attributes"]["table"] = [a for a in table if a.get("id") not in ids]
    return data


class TestMissingDefectData:
    """Missing critical defect data must not grade as a clean A (#134)."""

    @pytest.mark.parametrize("profile", ["abcdf", "binary"])
    def test_scsi_missing_grown_defects(self, mock_data_dir: Path, profile: str) -> None:
        from cdi_health.classes.config import get_config

        get_config().set_grading_profile(profile)
        data = copy.deepcopy(_load_mock(mock_data_dir, "scsi", "healthy_sas.json"))
        data.pop("scsi_grown_defect_list", None)
        device = _device_from_mock(data)
        assert device.reallocated_sectors is None  # not a -1 sentinel
        d = device.to_dict(pop=True)
        assert FLAG_MISSING_DEFECT_DATA in warning_flags(d)
        assert device.cdi_grade != "A"
        result = HealthScoreCalculator().calculate(d)
        assert result.grade == "B"
        assert any(x.field == "missing_defect_data" for x in result.deductions)

    def test_scsi_legacy_minus_one_sentinel_is_missing(self) -> None:
        device = {
            "transport_protocol": "SCSI",
            "smart_status": True,
            "reallocated_sectors": -1,
            "uncorrectable_errors": 0,
        }
        assert missing_defect_data(device) == ["grown_defects"]
        assert HealthScoreCalculator().calculate(device).grade == "B"

    @pytest.mark.parametrize("attr_ids", [(5,), (197,), (5, 197)])
    def test_ata_hdd_missing_realloc_or_pending(self, mock_data_dir: Path, attr_ids: tuple[int, ...]) -> None:
        data = _drop_ata_attrs(_load_mock(mock_data_dir, "ata", "healthy_hdd.json"), *attr_ids)
        device = _device_from_mock(data)
        d = device.to_dict(pop=True)
        assert FLAG_MISSING_DEFECT_DATA in warning_flags(d)
        assert device.cdi_grade == "B"
        if 5 in attr_ids:
            assert device.reallocated_sectors is None
            assert "reallocated_sectors" not in HealthScoreCalculator().calculate(d).attribute_grades

    def test_ata_hdd_missing_optional_198_not_flagged(self, mock_data_dir: Path) -> None:
        data = _drop_ata_attrs(_load_mock(mock_data_dir, "ata", "healthy_hdd.json"), 198)
        device = _device_from_mock(data)
        assert device.uncorrectable_errors is None
        assert FLAG_MISSING_DEFECT_DATA not in warning_flags(device.to_dict(pop=True))
        assert device.cdi_grade == "A"

    def test_ata_ssd_without_197_not_flagged(self, mock_data_dir: Path) -> None:
        # Many SSDs (Samsung, Intel) legitimately omit 197; only 5 is critical.
        data = _drop_ata_attrs(_load_mock(mock_data_dir, "ata", "MK000960GWSSD_healthy.json"), 197, 198)
        device = _device_from_mock(data)
        assert device.media_type == "SSD"
        assert FLAG_MISSING_DEFECT_DATA not in warning_flags(device.to_dict(pop=True))
        assert device.cdi_grade == "A"

    def test_nvme_missing_available_spare(self, mock_data_dir: Path) -> None:
        data = copy.deepcopy(_load_mock(mock_data_dir, "nvme", "SSDPE2KE032T8_healthy.json"))
        data["nvme_smart_health_information_log"].pop("available_spare", None)
        device = _device_from_mock(data)
        assert device.available_spare is None
        d = device.to_dict(pop=True)
        assert FLAG_MISSING_DEFECT_DATA in warning_flags(d)
        assert device.cdi_grade == "B"
        result = HealthScoreCalculator().calculate(d)
        # Unknown spare is not assumed 100 and not a fail-gate either
        assert not any(x.field == "available_spare" for x in result.deductions)

    def test_grade_cap_is_configurable(self, mock_data_dir: Path) -> None:
        from cdi_health.classes.config import get_config

        get_config().load_from_dict({"grading": {"missing_defect_data_grade_cap": "C"}})
        data = copy.deepcopy(_load_mock(mock_data_dir, "scsi", "healthy_sas.json"))
        data.pop("scsi_grown_defect_list", None)
        assert _device_from_mock(data).cdi_grade == "C"

    def test_ungraded_record_not_flagged(self) -> None:
        record = Devices._ungraded_placeholder({"name": "/dev/sdz", "error": "open failed", "protocol": "ATA"})
        assert missing_defect_data(record) == []
