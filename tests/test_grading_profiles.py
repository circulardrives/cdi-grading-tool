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
