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

"""Tests for health scoring system."""

from __future__ import annotations

import pytest

from cdi_health.classes.scoring import HealthScoreCalculator


class TestHealthScoreCalculator:
    """Test cases for HealthScoreCalculator."""

    def test_calculate_perfect_device(self) -> None:
        """Test scoring for a perfect device."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "NVME",  # Must use transport_protocol and be uppercase
            "smart_status": "PASSED",
            "reallocated_sectors": 0,
            "pending_sectors": 0,
            "uncorrectable_errors": 0,
            "temperature": 30,
            "percentage_used": 0,
        }

        result = calculator.calculate(device)

        assert result.score == 100
        assert result.grade == "A"
        assert result.status == "Excellent"
        assert result.is_certified is True
        assert len(result.deductions) == 0

    def test_calculate_failed_smart(self) -> None:
        """Test scoring for device with failed SMART status."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "NVME",  # Must use transport_protocol
            "smart_status": "FAILED",
        }

        result = calculator.calculate(device)

        # Failed SMART is a hard fail-gate, not a salvageable D grade.
        assert result.score == 0
        assert result.grade == "F"
        assert result.status == "Failed"
        assert result.is_certified is False
        assert any(d.severity == "critical" for d in result.deductions)
        assert any("SMART status failed" in d.reason for d in result.deductions)

    @pytest.mark.parametrize("smart_status", [False, "FAILED", "failed", "false", "bad"])
    def test_smart_fail_gate_forces_grade_f(self, smart_status: bool | str) -> None:
        """Partner 600-drive run: explicit SMART failures must be disposition failures."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "SCSI",
            "smart_supported": True,
            "smart_status": smart_status,
        }

        result = calculator.calculate(device)

        assert result.score == 0
        assert result.grade == "F"
        assert result.status == "Failed"
        assert result.is_certified is False
        assert any(d.field == "smart_status" and d.severity == "critical" for d in result.deductions)

    def test_failed_operational_state_forces_grade_f_even_when_smart_passes(self) -> None:
        """Partner 600-drive run: State=Fail with SMART passing is still a failed drive."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "SCSI",
            "state": "Fail",
            "smart_supported": True,
            "smart_status": "PASSED",
        }

        result = calculator.calculate(device)

        assert result.score == 0
        assert result.grade == "F"
        assert result.status == "Failed"
        assert result.is_certified is False
        assert any(d.field == "state" and d.severity == "critical" for d in result.deductions)

    def test_unresponsive_failed_state_forces_grade_f(self) -> None:
        """Partner 600-drive run: DOA/unresponsive drives should not become Grade D."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "SCSI",
            "state": "Fail",
            "smart_supported": False,
            "smart_status": "UNKNOWN",
            "capacity": 0,
            "power_on_hours": 0,
        }

        result = calculator.calculate(device)

        assert result.score == 0
        assert result.grade == "F"
        assert result.status == "Failed"
        assert result.is_certified is False
        assert any(d.field == "state" and d.severity == "critical" for d in result.deductions)

    def test_unknown_smart_without_failed_state_is_not_a_hard_fail(self) -> None:
        """Missing/unknown SMART alone should not hard-fail a drive without failed state evidence."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "SCSI",
            "smart_supported": False,
            "smart_status": "UNKNOWN",
        }

        result = calculator.calculate(device)

        assert result.score == 100
        assert result.grade == "A"

    def test_calculate_failed_selftest(self) -> None:
        """Test scoring for device with failed self-test."""
        calculator = HealthScoreCalculator()
        # Need to provide self-test log with failed entry and correct protocol
        device = {
            "transport_protocol": "NVME",  # Must be uppercase and use transport_protocol
            "smart_status": "PASSED",
            "nvme_self_test_log": {
                "current_self_test_operation": {"value": 0, "string": "No test in progress"},
                "current_self_test_completion": 0,
                "entries": [
                    {
                        "result": 1,  # Failed
                        "result_string": "Failed",
                        "type": 1,  # Short test
                        "type_string": "Short",
                        "completion_time": 0,
                    }
                ],
            },
        }

        result = calculator.calculate(device)

        # Failed self-test should result in score 0 and Grade F
        assert result.score == 0
        assert result.grade == "F"
        assert result.status == "Failed"
        assert result.is_certified is False
        assert any("self-test" in d.reason.lower() and "failed" in d.reason.lower() for d in result.deductions)

    def test_calculate_reallocated_sectors(self) -> None:
        """Test scoring with reallocated sectors at HDD failure threshold (10)."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "ATA",  # Must be uppercase and use transport_protocol
            "smart_status": "PASSED",
            "reallocated_sectors": 10,
        }

        result = calculator.calculate(device)

        # At the failure threshold, this is a critical health condition and hard-fails.
        assert result.score == 0
        assert result.grade == "F"
        assert any("reallocated" in d.reason.lower() for d in result.deductions)
        assert any(d.severity == "critical" and d.points == 10 for d in result.deductions)

    def test_grade_thresholds(self) -> None:
        """Test grade assignment at HDD sector defect boundaries."""
        calculator = HealthScoreCalculator()

        # At or below concern threshold (2): no deduction
        device_a = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "reallocated_sectors": 1,
        }
        result_a = calculator.calculate(device_a)
        assert result_a.grade == "A"
        assert result_a.score == 100

        # Mid range: 5 reallocated => (5-2)/(10-2)*10 ≈ 3.75 -> 4 pts
        device_b = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "reallocated_sectors": 5,
        }
        result_b = calculator.calculate(device_b)
        assert result_b.score == 96
        assert result_b.grade == "A"

    def test_hdd_reallocated_excess_beyond_failure_threshold(self) -> None:
        """Large reallocated counts on HDD should deduct beyond the M-at-F cap (CDI_HEALTH_SPEC)."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "media_type": "HDD",
            "reallocated_sectors": 48,
        }
        result = calculator.calculate(device)
        # M=10 + min(40, 38*1) = 48
        assert result.score == 0
        assert result.grade == "F"
        assert any(d.field == "reallocated_sectors" and d.points == 48 for d in result.deductions)

    def test_hdd_pending_excess_with_rotation_rate(self) -> None:
        """Infer HDD from rotation_rate when media_type is unset (mock-style dicts)."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "rotation_rate": 5400,
            "pending_sectors": 66,
        }
        result = calculator.calculate(device)
        # M=10 + min(40, 56) = 50
        assert result.score == 0
        assert result.grade == "F"
        assert any(d.field == "pending_sectors" and d.points == 50 for d in result.deductions)

    def test_ata_ssd_reallocated_per_sector_not_hdd_curve(self) -> None:
        """ATA SSDs use per-sector handling for reallocated count, not the HDD sector curve."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "media_type": "SSD",
            "reallocated_sectors": 10,
        }
        result = calculator.calculate(device)
        assert result.score == 50
        assert any(d.field == "reallocated_sectors" and d.points == 50 for d in result.deductions)

    def test_ata_ssd_inferred_from_rotation_rate_zero(self) -> None:
        """rotation_rate 0 implies SSD — reallocated uses SSD-style scoring."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "ATA",
            "smart_status": "PASSED",
            "rotation_rate": 0,
            "reallocated_sectors": 4,
        }
        result = calculator.calculate(device)
        assert result.score == 80
        assert any(d.field == "reallocated_sectors" and d.points == 20 for d in result.deductions)

    def test_critical_nvme_warning_forces_grade_f(self) -> None:
        """NVMe SMART critical warning bits are a hard fail-gate."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "NVME",
            "smart_status": "PASSED",
            "critical_warning": 1,
        }

        result = calculator.calculate(device)

        assert result.score == 0
        assert result.grade == "F"
        assert result.is_certified is False
        assert any(d.field == "critical_warning" and d.severity == "critical" for d in result.deductions)

    def test_nvme_available_spare_uses_device_threshold(self) -> None:
        """NVMe available spare should use the drive-reported threshold when present."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "NVME",
            "smart_status": "PASSED",
            "available_spare": 12,
            "available_spare_threshold": 10,
        }

        result = calculator.calculate(device)

        assert result.score == 100
        assert result.grade == "A"

        device["available_spare"] = 9
        result = calculator.calculate(device)

        assert result.score == 0
        assert result.grade == "F"
        assert any(d.field == "available_spare" and d.threshold == 10 for d in result.deductions)

    def test_nvme_media_errors_are_hard_failures(self) -> None:
        """NVMe media/data-integrity errors are critical, even when count is low."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "NVME",
            "smart_status": "PASSED",
            "media_errors": 1,
        }

        result = calculator.calculate(device)

        assert result.score == 0
        assert result.grade == "F"
        assert any(d.field == "media_errors" and d.severity == "critical" for d in result.deductions)

    def test_nvme_selftest_table_result_value_failure_forces_grade_f(self) -> None:
        """smartctl NVMe self-test JSON uses table[].self_test_result.value for failures."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "NVME",
            "smart_status": "PASSED",
            "nvme_self_test_log": {
                "current_self_test_operation": {"value": 0, "string": "No test in progress"},
                "table": [
                    {
                        "self_test_result": {"value": 1, "string": "The segment failed"},
                        "self_test_code": {"value": 2, "string": "Extended"},
                    }
                ],
            },
        }

        result = calculator.calculate(device)

        assert result.score == 0
        assert result.grade == "F"
        assert any(d.field == "nvme_self_test" and d.severity == "critical" for d in result.deductions)

    def test_nvme_failed_count_forces_grade_f_without_log_shape(self) -> None:
        """Device parsing can precompute failed self-test count from alternate log shapes."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "NVME",
            "smart_status": "PASSED",
            "nvme_self_test_failed_count": 1,
        }

        result = calculator.calculate(device)

        assert result.score == 0
        assert result.grade == "F"
        assert any(d.field == "nvme_self_test" and d.severity == "critical" for d in result.deductions)

    def test_nvme_missing_selftest_history_does_not_use_poh_as_score_input(self) -> None:
        """POH is telemetry; missing self-test history should not deduct from health score."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "NVME",
            "smart_status": "PASSED",
            "power_on_hours": 20000,
        }

        result = calculator.calculate(device)

        assert result.score == 100
        assert result.grade == "A"
        assert not any(d.field in {"nvme_self_test", "nvme_self_test_log"} for d in result.deductions)

    def test_scsi_offline_uncorrectable_alias_is_scored(self) -> None:
        """SCSI parser stores total uncorrected errors under offline_uncorrectable_sectors."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "SCSI",
            "smart_status": "PASSED",
            "offline_uncorrectable_sectors": 11,
        }

        result = calculator.calculate(device)

        assert result.score == 0
        assert result.grade == "F"
        assert any(d.field == "uncorrected_errors" and d.severity == "critical" for d in result.deductions)
