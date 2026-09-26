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

"""Tests for selectable grading profiles (binary vs abcdf) — issues #115 / #125."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cdi_health.classes.config import (
    GRADING_PROFILE_ABCDF,
    GRADING_PROFILE_BINARY,
    ThresholdConfig,
    normalize_grading_profile,
)
from cdi_health.classes.scoring import HealthScoreCalculator, calculate_health_score

FIXTURES = Path(__file__).parent / "fixtures" / "revert_standard"


@pytest.fixture(autouse=True)
def _reset_config() -> None:
    ThresholdConfig.reset_instance()
    yield
    ThresholdConfig.reset_instance()


class TestProfileNormalization:
    def test_aliases(self) -> None:
        assert normalize_grading_profile("passfail") == GRADING_PROFILE_BINARY
        assert normalize_grading_profile("revert") == GRADING_PROFILE_ABCDF
        assert normalize_grading_profile("graduated") == GRADING_PROFILE_ABCDF
        assert normalize_grading_profile("abcdf") == GRADING_PROFILE_ABCDF


class TestBinaryVsAbcdf:
    def test_default_profile_is_abcdf(self) -> None:
        assert ThresholdConfig.get_instance().grading_profile == GRADING_PROFILE_ABCDF

    def test_age_cap_only_in_abcdf(self) -> None:
        cfg = ThresholdConfig.get_instance()
        cfg.set_grading_profile("abcdf")
        assert cfg.age_cap_enabled is True
        device = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "power_on_hours": 65977,
        }
        assert calculate_health_score(device).grade == "D"

        cfg.set_grading_profile("binary")
        assert cfg.age_cap_enabled is False
        # Clean drive with high POH stays A under binary (POH telemetry only)
        assert calculate_health_score(device).grade == "A"

    def test_selftest_binary_instant_f_vs_abcdf_recency(self) -> None:
        device = {
            "transport_protocol": "NVME",
            "smart_status": "PASSED",
            "nvme_self_test_failed_count": 1,
        }
        cfg = ThresholdConfig.get_instance()
        cfg.set_grading_profile("binary")
        assert calculate_health_score(device).grade == "F"

        cfg.set_grading_profile("abcdf")
        result = calculate_health_score(device)
        assert result.grade == "D"
        assert result.attribute_grades["self_test_history"]["recent_failures"] == 1

    def test_scsi_graduated_bands_abcdf(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        # Grown defects 13 → C; uncorrected 6 → C; worst = C
        device = {
            "transport_protocol": "SCSI",
            "smart_status": True,
            "power_on_hours": 3000,
            "grown_defects": 13,
            "uncorrected_errors": 6,
        }
        result = calculate_health_score(device)
        assert result.grade == "C"
        assert result.certification == "true"
        assert result.attribute_grades["grown_defects"]["grade"] == "C"
        assert result.attribute_grades["uncorrected_errors"]["grade"] == "C"

    def test_multi_factor_degradation(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        # Three independent C-band attributes → escalate one level to D (§12.5)
        device = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "power_on_hours": 5000,
            "reallocated_sectors": 15,
            "pending_sectors": 15,
            "uncorrectable_errors": 10,
        }
        result = calculate_health_score(device)
        assert result.multi_factor_applied is True
        assert result.defect_grade == "D"
        assert result.grade == "D"
        assert result.certification == "Advisory"

    def test_tri_state_certification(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        calc = HealthScoreCalculator()
        assert calc.calculate({"transport_protocol": "ATA", "smart_status": "PASSED"}).certification == "true"
        d_grade = calc.calculate(
            {
                "transport_protocol": "ATA",
                "smart_status": "PASSED",
                "power_on_hours": 65000,
            }
        )
        assert d_grade.grade == "D"
        assert d_grade.certification == "Advisory"
        assert "Advisory" in d_grade.certification_rationale
        f_grade = calc.calculate({"transport_protocol": "ATA", "smart_status": "FAILED"})
        assert f_grade.certification == "false"


class TestReportSerialsAbcdf:
    """Finding 8 reconstructions from the gap-analysis report."""

    @pytest.mark.parametrize(
        "serial,expected",
        [
            ("1SHK383Z", "C"),
            ("JEHXTXVN", "C"),
            ("1SHKKWGZ", "C"),
            ("ZC19AACC", "C"),
            ("ZAD2AZ2A", "F"),
            ("ZAD2AX9T", "F"),
        ],
    )
    def test_report_serial_grade(self, serial: str, expected: str) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        # Flat reconstructions matching fixture metrics (scoring unit path)
        flat = {
            "1SHK383Z": {
                "transport_protocol": "SCSI",
                "smart_status": True,
                "power_on_hours": 3192,
                "grown_defects": 13,
                "uncorrected_errors": 6,
            },
            "JEHXTXVN": {
                "transport_protocol": "SCSI",
                "smart_status": True,
                "power_on_hours": 3190,
                "grown_defects": 31,
            },
            "1SHKKWGZ": {
                "transport_protocol": "SCSI",
                "smart_status": True,
                "power_on_hours": 3172,
                "grown_defects": 19,
                "uncorrected_errors": 11,
            },
            "ZC19AACC": {
                "transport_protocol": "SCSI",
                "smart_status": True,
                "power_on_hours": 30160,
                "grown_defects": 49,
            },
            "ZAD2AZ2A": {
                "transport_protocol": "SCSI",
                "smart_status": False,
                "power_on_hours": 41000,
                "grown_defects": 118,
                "uncorrected_errors": 42,
            },
            "ZAD2AX9T": {
                "transport_protocol": "SCSI",
                "smart_status": False,
                "power_on_hours": 39500,
                "grown_defects": 132,
                "uncorrected_errors": 53,
            },
        }
        result = calculate_health_score(flat[serial])
        assert result.grade == expected
        assert result.grading_profile == GRADING_PROFILE_ABCDF

    @pytest.mark.parametrize(
        "poh,protocol,expected",
        [
            (77889, "SCSI", "C"),
            (65977, "ATA", "D"),
            (23426, "ATA", "B"),
            (48324, "SCSI", "B"),
            (66343, "SCSI", "C"),
        ],
    )
    def test_age_cap_examples(self, poh: int, protocol: str, expected: str) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        device = {
            "transport_protocol": protocol,
            "smart_status": True if protocol == "SCSI" else "PASSED",
            "power_on_hours": poh,
            "grown_defects": 0,
            "reallocated_sectors": 0,
        }
        assert calculate_health_score(device).grade == expected


class TestSelftestRecencyAbcdf:
    def test_one_old_failure_is_c(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        device = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "power_on_hours": 15000,
            "smart_self_tests": [
                {
                    "status": {"passed": False, "string": "Completed: read failure"},
                    "lifetime_hours": 4000,
                }
            ],
        }
        result = calculate_health_score(device)
        assert result.grade == "C"
        assert result.attribute_grades["self_test_history"]["old_failures"] == 1

    def test_two_recent_failures_are_f(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        device = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "power_on_hours": 15000,
            "smart_self_tests": [
                {
                    "status": {"passed": False, "string": "Completed: read failure"},
                    "lifetime_hours": 14950,
                },
                {
                    "status": {"passed": False, "string": "Completed: read failure"},
                    "lifetime_hours": 14820,
                },
            ],
        }
        result = calculate_health_score(device)
        assert result.grade == "F"
        assert result.attribute_grades["self_test_history"]["recent_failures"] == 2

    def test_scsi_aggregate_hours(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        device = {
            "transport_protocol": "SCSI",
            "smart_status": True,
            "power_on_hours": 9000,
            "grown_defects": 0,
            "smart_self_tests": [
                {
                    "result": {"value": 3, "string": "Completed, medium failure"},
                    "power_on_time": {"aggregate": 4000},
                }
            ],
        }
        result = calculate_health_score(device)
        assert result.grade == "C"
        assert result.attribute_grades["self_test_history"]["old_failures"] == 1


class TestFixtureFilesExist:
    def test_revert_standard_fixtures_present(self) -> None:
        assert FIXTURES.is_dir()
        assert (FIXTURES / "report_1SHK383Z.json").is_file()
        data = json.loads((FIXTURES / "report_1SHK383Z.json").read_text())
        assert data["serial_number"] == "1SHK383Z"
        assert data["scsi_grown_defect_list"] == 13


def _nvme(pu: int | None = 0, spare: int | None = 100, avspt: int | None = 10) -> dict:
    device = {"transport_protocol": "NVME", "smart_status": True, "smart_data_readable": True}
    device["percentage_used"] = pu
    device["available_spare"] = spare
    if avspt is not None:
        device["available_spare_threshold"] = avspt
    return device


class TestWearAndSparePolicy:
    """#133: wear below 100% is points-only; available spare is graded."""

    def test_nvme_wear_tiers_lower_score_not_grade(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        results = [calculate_health_score(_nvme(pu=pu)) for pu in (79, 85, 95)]
        assert [r.grade for r in results] == ["A", "A", "A"]
        scores = [r.score for r in results]
        assert scores[0] > scores[1] > scores[2]
        assert scores == [100, 95, 90]
        # Tier deductions are visible and non-graduated
        assert not any(d.field == "percentage_used" for d in results[0].deductions)
        wear = [d for d in results[2].deductions if d.field == "percentage_used"]
        assert wear and wear[0].attribute_grade is None and wear[0].severity == "warning"
        assert "percentage_used" not in results[2].attribute_grades

    def test_wear_tiers_are_inclusive_at_boundary(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        assert calculate_health_score(_nvme(pu=80)).score == 95
        assert calculate_health_score(_nvme(pu=90)).score == 90

    @pytest.mark.parametrize("pu", [100, 101, 150])
    def test_wear_at_or_past_endurance_grades_c(self, pu: int) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        result = calculate_health_score(_nvme(pu=pu))
        assert result.grade == "C"
        assert result.certification == "true"
        assert not result.fail_gates
        assert result.attribute_grades["endurance"]["grade"] == "C"

    def test_wear_past_endurance_with_other_warning_grades_d(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        # spare 70 is its own B attribute: any other warning drops endurance to D
        result = calculate_health_score(_nvme(pu=100, spare=70))
        assert result.attribute_grades["endurance"]["grade"] == "D"
        assert result.grade == "D"
        assert result.certification == "Advisory"

    def test_wear_past_endurance_worse_attribute_still_wins(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        assert calculate_health_score(_nvme(pu=100, spare=5)).grade == "F"

    def test_endurance_exceeded_grade_f_restores_fail_gate(self) -> None:
        config = ThresholdConfig.get_instance()
        config.set_grading_profile("abcdf")
        config._config["nvme"]["endurance_exceeded_grade"] = "F"
        try:
            result = calculate_health_score(_nvme(pu=101))
        finally:
            config._config["nvme"]["endurance_exceeded_grade"] = "C"
        assert result.grade == "F"
        assert result.fail_gates

    def test_binary_profile_wear_over_100_still_fails(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("binary")
        assert calculate_health_score(_nvme(pu=101)).grade == "F"

    def test_endurance_exceeded_warning_flag(self) -> None:
        from cdi_health.classes.revert import FLAG_ENDURANCE_EXCEEDED, warning_flags

        assert FLAG_ENDURANCE_EXCEEDED in warning_flags(_nvme(pu=100))
        assert FLAG_ENDURANCE_EXCEEDED not in warning_flags(_nvme(pu=99))

    @pytest.mark.parametrize(
        ("spare", "avspt", "grade"),
        [(100, 10, "A"), (80, 10, "A"), (70, 10, "B"), (45, 10, "C"), (20, 10, "D"), (10, 10, "D"), (5, 10, "F")],
    )
    def test_nvme_available_spare_bands(self, spare: int, avspt: int, grade: str) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        result = calculate_health_score(_nvme(spare=spare, avspt=avspt))
        assert result.grade == grade
        info = result.attribute_grades["available_spare"]
        assert info == {"value": spare, "grade": grade, "threshold": avspt}

    def test_spare_feeds_multi_factor(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        device = _nvme(spare=45)  # C
        device["nvme_self_test_log"] = {
            "entries": [{"self_test_result": {"value": 7}, "power_on_hours": 0} for _ in range(1)]
        }
        device["power_on_hours"] = 5000  # one old failure -> C
        result = calculate_health_score(device)
        assert result.attribute_grades["available_spare"]["grade"] == "C"
        assert result.attribute_grades["self_test_history"]["grade"] == "C"
        assert result.grade == "C"  # only two C-or-worse attributes: no escalation

    def test_spare_threshold_fallback_from_yaml(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        result = calculate_health_score(_nvme(spare=8, avspt=None))
        assert result.grade == "F"  # below minimum_available_spare fallback (10)

    def test_binary_spare_d_range_warning(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("binary")
        healthy = calculate_health_score(_nvme(spare=70))
        assert healthy.score == 100
        low = calculate_health_score(_nvme(spare=20))
        assert low.score == 90
        assert any(d.field == "available_spare" and d.severity == "warning" for d in low.deductions)
        assert calculate_health_score(_nvme(spare=5)).grade == "F"

    def test_binary_wear_tiers(self) -> None:
        ThresholdConfig.get_instance().set_grading_profile("binary")
        assert [calculate_health_score(_nvme(pu=pu)).score for pu in (79, 80, 90)] == [100, 95, 90]

    def test_missing_spare_warning_flag(self) -> None:
        from cdi_health.classes.revert import FLAG_MISSING_DEFECT_DATA, warning_flags

        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        device = _nvme(spare=None)
        result = calculate_health_score(device)
        assert "available_spare" not in result.attribute_grades
        assert result.grade == "B"
        assert FLAG_MISSING_DEFECT_DATA in warning_flags(device)

    @pytest.mark.parametrize("profile", ["abcdf", "binary"])
    def test_ata_ssd_wear_tiers(self, profile: str) -> None:
        ThresholdConfig.get_instance().set_grading_profile(profile)
        base = {"transport_protocol": "ATA", "media_type": "SSD", "smart_status": True, "reallocated_sectors": 0}
        scores = [calculate_health_score({**base, "ssd_percentage_used_endurance": pu}).score for pu in (79, 80, 90)]
        assert scores == [100, 95, 90]
        # 0% used must not fall through to another field (was `a or b`)
        zero = calculate_health_score({**base, "ssd_percentage_used_endurance": 0, "percentage_used": 95})
        assert zero.score == 100

    @pytest.mark.parametrize("profile", ["abcdf", "binary"])
    def test_sas_ssd_wear_tiers(self, profile: str) -> None:
        ThresholdConfig.get_instance().set_grading_profile(profile)
        base = {"transport_protocol": "SCSI", "smart_status": True, "grown_defects": 0, "uncorrectable_errors": 0}
        scores = [calculate_health_score({**base, "ssd_percentage_used_endurance": pu}).score for pu in (79, 85, 95)]
        assert scores == [100, 95, 90]

    @pytest.mark.parametrize(("value", "grade"), [(100, "A"), (70, "B"), (45, "C"), (20, "D"), (4, "F")])
    def test_ata_reserved_space_bands(self, value: int, grade: str) -> None:
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        device = {
            "transport_protocol": "ATA",
            "media_type": "SSD",
            "smart_status": True,
            "reallocated_sectors": 0,
            "available_reserved_space": value,
            "available_reserved_space_threshold": 4,
        }
        result = calculate_health_score(device)
        assert result.grade == grade
        assert result.attribute_grades["available_reserved_space"]["grade"] == grade

    def test_ata_232_parsed_only_when_named_reserved_space(self) -> None:
        from cdi_health.classes.mock import create_mock_device

        mock_dir = Path(__file__).parent.parent / "src" / "cdi_health" / "mock_data" / "ata"
        with (mock_dir / "SDSSDH3_512G_healthy.json").open() as f:
            data = json.load(f)
        device = create_mock_device(mock_data=data)
        assert device.available_reserved_space == 100
        assert device.available_reserved_space_threshold == 4

        for attr in data["ata_smart_attributes"]["table"]:
            if attr["id"] == 232:
                attr["name"] = "Unknown_Attribute"
        assert create_mock_device(mock_data=data).available_reserved_space is None

    def test_spare_bands_configurable_and_validated(self) -> None:
        from cdi_health.classes.config import ConfigError

        cfg = ThresholdConfig.get_instance()
        cfg.load_from_dict({"nvme": {"available_spare_bands": {"A": 90, "B": 70, "C": 50}}})
        cfg.set_grading_profile("abcdf")
        assert calculate_health_score(_nvme(spare=85)).grade == "B"
        with pytest.raises(ConfigError):
            cfg.load_from_dict({"nvme": {"available_spare_bands": {"A": 40, "B": 60}}})
