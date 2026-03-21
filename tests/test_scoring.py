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

        # Failed SMART deducts 50 points, so score is 50 (not 0)
        # But it should still be Grade D or F due to critical failure
        assert result.score == 50  # 100 - 50 = 50
        assert result.grade in ("D", "F")  # Grade D (50 points)
        assert result.is_certified is False
        assert any(d.severity == "critical" for d in result.deductions)
        assert any("SMART status failed" in d.reason for d in result.deductions)

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
        """Test scoring with reallocated sectors."""
        calculator = HealthScoreCalculator()
        device = {
            "transport_protocol": "ATA",  # Must be uppercase and use transport_protocol
            "smart_status": "PASSED",
            "reallocated_sectors": 10,
        }

        result = calculator.calculate(device)

        # Reallocated sectors should cause deductions
        # 10 sectors * 5 points = 50 points deduction (capped at 50)
        assert result.score < 100
        assert any("reallocated" in d.reason.lower() for d in result.deductions)

    def test_grade_thresholds(self) -> None:
        """Test grade assignment at threshold boundaries."""
        calculator = HealthScoreCalculator()

        # Test A grade (90-100) - need to ensure score is in range
        device_a = {
            "transport_protocol": "ATA",  # Must use transport_protocol
            "smart_status": "PASSED",
            "reallocated_sectors": 1,  # -5 points = 95 (A grade)
        }
        result_a = calculator.calculate(device_a)
        assert result_a.grade == "A"
        assert result_a.score == 95

        # Test B grade (75-89) - need enough deductions
        device_b = {
            "transport_protocol": "ATA",  # Must use transport_protocol
            "smart_status": "PASSED",
            "reallocated_sectors": 5,  # -25 points = 75 (B grade)
        }
        result_b = calculator.calculate(device_b)
        # Score should be 75, which is exactly at B threshold
        assert result_b.score == 75
        assert result_b.grade == "B"
