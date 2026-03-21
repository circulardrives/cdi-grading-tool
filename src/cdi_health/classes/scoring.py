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

"""
Health Scoring System for CDI Health

Provides 0-100 numeric health scores aligned with CDI specifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cdi_health.classes.config import get_config


@dataclass
class ScoreDeduction:
    """Represents a deduction from the health score."""

    reason: str
    points: int
    severity: str  # "info", "warning", "critical"
    field: str = None
    value: Any = None
    threshold: Any = None

    def __str__(self) -> str:
        if self.threshold is not None:
            return f"{self.reason}: {self.value} (threshold: {self.threshold}) [-{self.points}]"
        return f"{self.reason} [-{self.points}]"


@dataclass
class HealthScore:
    """Complete health score with breakdown."""

    score: int
    grade: str
    status: str
    deductions: list[ScoreDeduction]
    is_certified: bool

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "health_score": self.score,
            "health_grade": self.grade,
            "health_status": self.status,
            "is_certified": self.is_certified,
            "deductions": [
                {
                    "reason": d.reason,
                    "points": d.points,
                    "severity": d.severity,
                    "field": d.field,
                    "value": d.value,
                    "threshold": d.threshold,
                }
                for d in self.deductions
            ],
        }


class HealthScoreCalculator:
    """
    Calculate 0-100 health scores from device metrics.

    Scoring Formula (CDI-Spec Aligned):
    - Base Score: 100
    - SMART Status Failed: -50 points (results in Grade F)
    - Failed Self-Test: -50 points (results in Grade F - drive is bad)
    - Per Reallocated Sector: -5 points (up to threshold)
    - Per Pending Sector: -5 points (up to threshold)
    - Per Uncorrectable Error: -5 points (up to threshold)
    - Exceeds Any Threshold: -25 points (triggers Grade F)
    - Temperature Warning: -5 points
    - Temperature Critical: -15 points
    """

    # Score to Grade mapping
    GRADE_THRESHOLDS = [
        (90, "A", "Excellent"),
        (75, "B", "Good"),
        (60, "C", "Fair"),
        (40, "D", "Poor"),
        (0, "F", "Failed"),
    ]

    # Points deductions
    SMART_FAILURE_DEDUCTION = 50
    PER_SECTOR_DEDUCTION = 5
    THRESHOLD_EXCEEDED_DEDUCTION = 25
    TEMP_WARNING_DEDUCTION = 5
    TEMP_CRITICAL_DEDUCTION = 15

    def __init__(self):
        """Initialize the health score calculator."""
        self.config = get_config()

    def calculate(self, device: dict) -> HealthScore:
        """
        Calculate health score for a device.

        :param device: Device dictionary with metrics
        :return: HealthScore object
        """
        score = 100
        deductions = []

        # Get device protocol type
        protocol = device.get("transport_protocol", "").upper()

        # Check SMART status
        smart_deductions = self._check_smart_status(device)
        deductions.extend(smart_deductions)
        score -= sum(d.points for d in smart_deductions)

        # Protocol-specific checks
        if protocol == "ATA":
            ata_deductions = self._check_ata_metrics(device)
            deductions.extend(ata_deductions)
            score -= sum(d.points for d in ata_deductions)
        elif protocol == "NVME":
            nvme_deductions = self._check_nvme_metrics(device)
            deductions.extend(nvme_deductions)
            score -= sum(d.points for d in nvme_deductions)
        elif protocol == "SCSI":
            scsi_deductions = self._check_scsi_metrics(device)
            deductions.extend(scsi_deductions)
            score -= sum(d.points for d in scsi_deductions)

        # Check temperature
        temp_deductions = self._check_temperature(device)
        deductions.extend(temp_deductions)
        score -= sum(d.points for d in temp_deductions)

        # Clamp score to 0-100
        score = max(0, min(100, score))

        # Check for failed self-test - this is a hard failure, drive is bad
        has_failed_selftest = any("failed" in d.reason.lower() and "self-test" in d.reason.lower() for d in deductions)

        # Determine grade and status
        # If self-test failed, Grade F regardless of score
        if has_failed_selftest:
            grade = "F"
            status = "Failed"
            score = 0  # Set score to 0 to reflect complete failure
        else:
            grade = self.get_grade(score)
            status = self.get_status_text(score)

        # Determine certification (Grade A or B)
        # Failed self-test = automatic failure, cannot be certified
        is_certified = (
            grade in ("A", "B") and not any(d.severity == "critical" for d in deductions) and not has_failed_selftest
        )

        return HealthScore(
            score=score,
            grade=grade,
            status=status,
            deductions=deductions,
            is_certified=is_certified,
        )

    def _check_smart_status(self, device: dict) -> list[ScoreDeduction]:
        """Check SMART status and self-test results."""
        deductions = []

        smart_status = device.get("smart_status", "")

        # Handle boolean values
        if isinstance(smart_status, bool):
            if not smart_status:
                deductions.append(
                    ScoreDeduction(
                        reason="SMART status failed",
                        points=self.SMART_FAILURE_DEDUCTION,
                        severity="critical",
                        field="smart_status",
                        value="Failed",
                    )
                )
            return deductions

        # Handle string values
        if smart_status:
            smart_status_lower = str(smart_status).lower()
            if smart_status_lower not in ("pass", "passed", "ok", "true"):
                deductions.append(
                    ScoreDeduction(
                        reason="SMART status failed",
                        points=self.SMART_FAILURE_DEDUCTION,
                        severity="critical",
                        field="smart_status",
                        value=smart_status,
                    )
                )

        return deductions

    def _check_ata_metrics(self, device: dict) -> list[ScoreDeduction]:
        """Check ATA-specific metrics."""
        deductions = []

        # Reallocated sectors
        reallocated = device.get("reallocated_sectors", 0) or 0
        if reallocated > 0:
            threshold = self.config.maximum_reallocated_sectors
            points = min(reallocated * self.PER_SECTOR_DEDUCTION, 50)

            if reallocated > threshold:
                points += self.THRESHOLD_EXCEEDED_DEDUCTION
                severity = "critical"
            else:
                severity = "warning"

            deductions.append(
                ScoreDeduction(
                    reason="Reallocated sectors",
                    points=points,
                    severity=severity,
                    field="reallocated_sectors",
                    value=reallocated,
                    threshold=threshold,
                )
            )

        # Pending sectors
        pending = device.get("pending_sectors", 0) or 0
        if pending > 0:
            threshold = self.config.maximum_pending_sectors
            points = min(pending * self.PER_SECTOR_DEDUCTION, 50)

            if pending > threshold:
                points += self.THRESHOLD_EXCEEDED_DEDUCTION
                severity = "critical"
            else:
                severity = "warning"

            deductions.append(
                ScoreDeduction(
                    reason="Pending sectors",
                    points=points,
                    severity=severity,
                    field="pending_sectors",
                    value=pending,
                    threshold=threshold,
                )
            )

        # Uncorrectable errors
        uncorrectable = device.get("uncorrectable_errors", 0) or 0
        if uncorrectable > 0:
            threshold = self.config.maximum_uncorrectable_errors
            points = min(uncorrectable * self.PER_SECTOR_DEDUCTION, 50)

            if uncorrectable > threshold:
                points += self.THRESHOLD_EXCEEDED_DEDUCTION
                severity = "critical"
            else:
                severity = "warning"

            deductions.append(
                ScoreDeduction(
                    reason="Uncorrectable errors",
                    points=points,
                    severity=severity,
                    field="uncorrectable_errors",
                    value=uncorrectable,
                    threshold=threshold,
                )
            )

        # Offline uncorrectable sectors
        offline = device.get("offline_uncorrectable_sectors", 0) or 0
        if offline > 0:
            threshold = self.config.maximum_uncorrectable_errors
            points = min(offline * self.PER_SECTOR_DEDUCTION, 50)

            if offline > threshold:
                points += self.THRESHOLD_EXCEEDED_DEDUCTION
                severity = "critical"
            else:
                severity = "warning"

            deductions.append(
                ScoreDeduction(
                    reason="Offline uncorrectable sectors",
                    points=points,
                    severity=severity,
                    field="offline_uncorrectable_sectors",
                    value=offline,
                    threshold=threshold,
                )
            )

        # SSD Percentage Used Endurance (for ATA SSDs)
        # Check both ssd_percentage_used_endurance and percentage_used fields
        pct_used = device.get("ssd_percentage_used_endurance") or device.get("percentage_used")
        if pct_used is not None and pct_used >= 0:
            threshold = self.config.maximum_ssd_percentage_used
            if pct_used > threshold:
                deductions.append(
                    ScoreDeduction(
                        reason="SSD percentage used exceeds threshold",
                        points=self.THRESHOLD_EXCEEDED_DEDUCTION,
                        severity="critical",
                        field="ssd_percentage_used_endurance",
                        value=pct_used,
                        threshold=threshold,
                    )
                )
            elif pct_used > 90:
                deductions.append(
                    ScoreDeduction(
                        reason="High SSD percentage used",
                        points=10,
                        severity="warning",
                        field="ssd_percentage_used_endurance",
                        value=pct_used,
                    )
                )
            elif pct_used > 80:
                deductions.append(
                    ScoreDeduction(
                        reason="Moderate SSD percentage used",
                        points=5,
                        severity="info",
                        field="ssd_percentage_used_endurance",
                        value=pct_used,
                    )
                )

        return deductions

    def _check_nvme_metrics(self, device: dict) -> list[ScoreDeduction]:
        """Check NVMe-specific metrics."""
        deductions = []

        # Percentage used
        pct_used = device.get("percentage_used", 0) or 0
        threshold = self.config.maximum_ssd_percentage_used
        if pct_used > threshold:
            deductions.append(
                ScoreDeduction(
                    reason="Percentage used exceeds threshold",
                    points=self.THRESHOLD_EXCEEDED_DEDUCTION,
                    severity="critical",
                    field="percentage_used",
                    value=pct_used,
                    threshold=threshold,
                )
            )
        elif pct_used > 90:
            deductions.append(
                ScoreDeduction(
                    reason="High percentage used",
                    points=10,
                    severity="warning",
                    field="percentage_used",
                    value=pct_used,
                    threshold=threshold,
                )
            )

        # Available spare
        spare = device.get("available_spare", 100) or 100
        threshold = self.config.minimum_ssd_available_spare
        if spare < threshold:
            deductions.append(
                ScoreDeduction(
                    reason="Available spare below threshold",
                    points=self.THRESHOLD_EXCEEDED_DEDUCTION,
                    severity="critical",
                    field="available_spare",
                    value=spare,
                    threshold=threshold,
                )
            )

        # Critical warning
        critical_warning = device.get("critical_warning", 0) or 0
        if critical_warning > 0:
            deductions.append(
                ScoreDeduction(
                    reason="NVMe critical warning active",
                    points=self.SMART_FAILURE_DEDUCTION,
                    severity="critical",
                    field="critical_warning",
                    value=critical_warning,
                )
            )

        # Media errors
        media_errors = device.get("media_errors", 0) or 0
        if media_errors > 0:
            points = min(media_errors * self.PER_SECTOR_DEDUCTION, 50)
            deductions.append(
                ScoreDeduction(
                    reason="Media errors detected",
                    points=points,
                    severity="critical" if media_errors > 10 else "warning",
                    field="media_errors",
                    value=media_errors,
                )
            )

        # Self-test results
        self_test_deductions = self._check_nvme_selftest(device)
        deductions.extend(self_test_deductions)

        return deductions

    def _check_nvme_selftest(self, device: dict) -> list[ScoreDeduction]:
        """Check NVMe self-test results."""
        deductions = []

        # Check for self-test log data
        self_test_log = device.get("nvme_self_test_log")
        if not self_test_log:
            # No self-test data available - minor warning if device is older
            poh = device.get("power_on_hours", 0) or 0
            if poh > 8760:  # More than 1 year
                deductions.append(
                    ScoreDeduction(
                        reason="No self-test history available",
                        points=2,
                        severity="info",
                        field="nvme_self_test_log",
                        value=None,
                    )
                )
            return deductions

        # Check current operation
        current_op = self_test_log.get("current_self_test_operation", {})
        op_value = current_op.get("value", 0)

        # Check for failed tests in history
        entries = self_test_log.get("entries", [])
        if entries:
            # Check most recent entries for failures
            recent_failures = []
            for entry in entries[:5]:  # Check last 5 tests
                result = entry.get("result", 0)
                if result == 1:  # Failed
                    recent_failures.append(entry)

            if recent_failures:
                # FAILED SELF-TEST = CRITICAL FAILURE
                # This should result in Grade F, similar to SMART failure
                # Use maximum deduction to ensure Grade F
                for failure in recent_failures:
                    test_type = failure.get("type", 0)
                    if test_type == 2:  # Extended test failure
                        deductions.append(
                            ScoreDeduction(
                                reason="Failed extended self-test - Drive is failing",
                                points=self.SMART_FAILURE_DEDUCTION,  # -50 points (same as SMART failure)
                                severity="critical",
                                field="nvme_self_test",
                                value="Failed",
                            )
                        )
                    else:  # Short test failure
                        # Short test failure is also critical - if short test fails, drive is bad
                        deductions.append(
                            ScoreDeduction(
                                reason="Failed short self-test - Drive is failing",
                                points=self.SMART_FAILURE_DEDUCTION,  # -50 points (same as SMART failure)
                                severity="critical",
                                field="nvme_self_test",
                                value="Failed",
                            )
                        )

        # Check if no recent self-test (warn if device has been used)
        # This would require timestamp parsing, simplified here
        if not entries:
            poh = device.get("power_on_hours", 0) or 0
            if poh > 720:  # More than 30 days
                deductions.append(
                    ScoreDeduction(
                        reason="No self-test run in last 30 days",
                        points=5,
                        severity="warning",
                        field="nvme_self_test",
                        value="No tests logged",
                    )
                )

        return deductions

    def _check_scsi_metrics(self, device: dict) -> list[ScoreDeduction]:
        """Check SCSI-specific metrics."""
        deductions = []

        # Grown defects
        grown_defects = device.get("grown_defects", 0) or 0
        if grown_defects > 0:
            threshold = self.config.maximum_grown_defects
            points = min(grown_defects * self.PER_SECTOR_DEDUCTION, 50)

            if grown_defects > threshold:
                points += self.THRESHOLD_EXCEEDED_DEDUCTION
                severity = "critical"
            else:
                severity = "warning"

            deductions.append(
                ScoreDeduction(
                    reason="Grown defects",
                    points=points,
                    severity=severity,
                    field="grown_defects",
                    value=grown_defects,
                    threshold=threshold,
                )
            )

        # Uncorrected errors
        uncorrected = device.get("uncorrected_errors", 0) or 0
        if uncorrected > 0:
            threshold = self.config.maximum_scsi_uncorrected_errors
            points = min(uncorrected * self.PER_SECTOR_DEDUCTION, 50)

            if uncorrected > threshold:
                points += self.THRESHOLD_EXCEEDED_DEDUCTION
                severity = "critical"
            else:
                severity = "warning"

            deductions.append(
                ScoreDeduction(
                    reason="Uncorrected read/write errors",
                    points=points,
                    severity=severity,
                    field="uncorrected_errors",
                    value=uncorrected,
                    threshold=threshold,
                )
            )

        return deductions

    def _check_temperature(self, device: dict) -> list[ScoreDeduction]:
        """Check temperature metrics."""
        deductions = []

        temp = device.get("current_temperature")
        if temp is None:
            return deductions

        warning_temp = self.config.warning_temperature
        max_temp = self.config.maximum_operating_temperature

        if temp > max_temp:
            deductions.append(
                ScoreDeduction(
                    reason="Temperature critical",
                    points=self.TEMP_CRITICAL_DEDUCTION,
                    severity="critical",
                    field="current_temperature",
                    value=temp,
                    threshold=max_temp,
                )
            )
        elif temp > warning_temp:
            deductions.append(
                ScoreDeduction(
                    reason="Temperature warning",
                    points=self.TEMP_WARNING_DEDUCTION,
                    severity="warning",
                    field="current_temperature",
                    value=temp,
                    threshold=warning_temp,
                )
            )

        return deductions

    def get_grade(self, score: int) -> str:
        """
        Get letter grade from numeric score.

        :param score: Numeric score 0-100
        :return: Letter grade (A, B, C, D, F)
        """
        for threshold, grade, _ in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"

    def get_status_text(self, score: int) -> str:
        """
        Get status text from numeric score.

        :param score: Numeric score 0-100
        :return: Status text (Excellent, Good, Fair, Poor, Failed)
        """
        for threshold, _, status in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return status
        return "Failed"


def calculate_health_score(device: dict) -> HealthScore:
    """
    Convenience function to calculate health score for a device.

    :param device: Device dictionary with metrics
    :return: HealthScore object
    """
    calculator = HealthScoreCalculator()
    return calculator.calculate(device)
