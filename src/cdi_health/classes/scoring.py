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
    - SATA/SAS HDD — reallocated, pending, and SCSI grown defects: no deduction at or below
      the concern threshold (default 2); above that, linear deduction up to M points at failure
      threshold F; counts beyond F add extra deduction (capped) so large defect counts grade down.
      ATA SSDs use per-sector style for reallocated/pending (same scale as offline uncorrectable), not the HDD curve.
    - Per Uncorrectable Error (ATA offline/uncorrectable, SCSI uncorrected): -5 points (up to threshold)
    - Exceeds uncorrectable threshold: -25 points (critical)
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

        # Check hard fail-gates first: operational state and SMART status.
        # These conditions mean the drive should not be dispositioned as salvageable.
        state_deductions = self._check_operational_state(device)
        deductions.extend(state_deductions)
        score -= sum(d.points for d in state_deductions)

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

        # Check for hard failures - critical health conditions are not salvageable grades.
        has_failed_selftest = any("failed" in d.reason.lower() and "self-test" in d.reason.lower() for d in deductions)
        has_hard_failure = any(d.severity == "critical" for d in deductions)

        # Determine grade and status
        # If a critical health condition exists, Grade F regardless of numeric deductions.
        if has_failed_selftest or has_hard_failure:
            grade = "F"
            status = "Failed"
            score = 0  # Set score to 0 to reflect complete failure
        else:
            grade = self.get_grade(score)
            status = self.get_status_text(score)

        # Determine certification (Grade A or B). Critical health conditions are automatic failures.
        is_certified = (
            grade in ("A", "B")
            and not any(d.severity == "critical" for d in deductions)
            and not has_failed_selftest
            and not has_hard_failure
        )

        return HealthScore(
            score=score,
            grade=grade,
            status=status,
            deductions=deductions,
            is_certified=is_certified,
        )

    def _check_operational_state(self, device: dict) -> list[ScoreDeduction]:
        """Check top-level operational state from the scan/disposition path."""
        state = device.get("state") or device.get("State")
        if str(state).strip().lower() != "fail":
            return []

        return [
            ScoreDeduction(
                reason="Device operational state failed",
                points=self.SMART_FAILURE_DEDUCTION,
                severity="critical",
                field="state",
                value=state,
            )
        ]

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
            if smart_status_lower in ("fail", "failed", "false", "bad"):
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

    @staticmethod
    def _rotation_rpm(device: dict) -> int | None:
        """Parse rotation_rate from device dict; None if unknown."""
        rr = device.get("rotation_rate")
        if isinstance(rr, int):
            return rr
        if isinstance(rr, str):
            s = rr.strip().upper()
            if s in ("", "NOT REPORTED", "NONE"):
                return None
            if s.isdigit():
                return int(s)
        return None

    @classmethod
    def _use_hdd_sector_defect_curve(cls, device: dict) -> bool:
        """True for rotating HDDs; False for SSDs (per CDI spec HDD sector curve scope)."""
        mt = str(device.get("media_type") or "").strip().upper()
        if mt == "SSD":
            return False
        if mt == "HDD":
            return True
        rpm = cls._rotation_rpm(device)
        if rpm is not None:
            return rpm > 0
        proto = str(device.get("transport_protocol") or "").strip().upper()
        if proto == "ATA":
            return True
        if proto in ("SCSI", "SAS"):
            return True
        return True

    def _deduction_ssd_style_defect_count(
        self,
        count: int,
        *,
        threshold: int,
        reason: str,
        field: str,
    ) -> ScoreDeduction | None:
        """ATA SSD reallocated/pending: same per-sector model as offline uncorrectable (spec)."""
        if count <= 0:
            return None
        points = min(count * self.PER_SECTOR_DEDUCTION, 50)
        if count > threshold:
            points += self.THRESHOLD_EXCEEDED_DEDUCTION
            severity = "critical"
        else:
            severity = "warning"
        return ScoreDeduction(
            reason=reason,
            points=points,
            severity=severity,
            field=field,
            value=count,
            threshold=threshold,
        )

    def _deduction_hdd_sector_defect(
        self,
        count: int,
        *,
        failure_threshold: int,
        reason: str,
        field: str,
    ) -> ScoreDeduction | None:
        """
        SATA/SAS HDD-style defect counts: no deduction at or below concern threshold;
        linear scale to max deduction points at failure threshold; beyond F, extra capped deduction.
        """
        concern = self.config.hdd_sector_concern_threshold
        max_pt = self.config.hdd_sector_defect_max_deduction_points
        per_excess = self.config.hdd_sector_excess_points_per_sector
        excess_cap = self.config.hdd_sector_excess_cap
        if count <= concern:
            return None
        span = failure_threshold - concern
        if span < 1:
            span = 1
        if count >= failure_threshold:
            excess = count - failure_threshold
            extra = min(excess_cap, excess * per_excess)
            points = min(50, max_pt + extra)
            return ScoreDeduction(
                reason=reason,
                points=points,
                severity="critical",
                field=field,
                value=count,
                threshold=failure_threshold,
            )
        raw_pts = int(round((count - concern) / span * max_pt))
        points = max(1, min(max_pt - 1, raw_pts))
        return ScoreDeduction(
            reason=reason,
            points=points,
            severity="warning",
            field=field,
            value=count,
            threshold=failure_threshold,
        )

    def _check_ata_metrics(self, device: dict) -> list[ScoreDeduction]:
        """Check ATA-specific metrics."""
        deductions = []

        use_hdd_curve = self._use_hdd_sector_defect_curve(device)

        # Reallocated sectors
        reallocated = int(device.get("reallocated_sectors", 0) or 0)
        if use_hdd_curve:
            d = self._deduction_hdd_sector_defect(
                reallocated,
                failure_threshold=self.config.maximum_reallocated_sectors,
                reason="Reallocated sectors",
                field="reallocated_sectors",
            )
        else:
            d = self._deduction_ssd_style_defect_count(
                reallocated,
                threshold=self.config.maximum_reallocated_sectors,
                reason="Reallocated sectors",
                field="reallocated_sectors",
            )
        if d:
            deductions.append(d)

        # Pending sectors
        pending_raw = device.get("pending_sectors")
        if pending_raw is None:
            pending_raw = device.get("pending_reallocated_sectors")
        pending = int(pending_raw or 0)
        if use_hdd_curve:
            d = self._deduction_hdd_sector_defect(
                pending,
                failure_threshold=self.config.maximum_pending_sectors,
                reason="Pending sectors",
                field="pending_sectors",
            )
        else:
            d = self._deduction_ssd_style_defect_count(
                pending,
                threshold=self.config.maximum_pending_sectors,
                reason="Pending sectors",
                field="pending_sectors",
            )
        if d:
            deductions.append(d)

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
        spare = device.get("available_spare")
        if spare is None:
            spare = 100
        threshold = device.get("available_spare_threshold")
        if threshold is None:
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
            deductions.append(
                ScoreDeduction(
                    reason="Media errors detected",
                    points=self.SMART_FAILURE_DEDUCTION,
                    severity="critical",
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
        if (device.get("nvme_self_test_failed_count") or 0) > 0:
            deductions.append(
                ScoreDeduction(
                    reason="Failed NVMe self-test - Drive is failing",
                    points=self.SMART_FAILURE_DEDUCTION,
                    severity="critical",
                    field="nvme_self_test",
                    value="Failed",
                )
            )
            return deductions

        if not self_test_log:
            # Absence of self-test history is reported elsewhere; it is not a POH-based score deduction.
            return deductions

        # Check current operation
        current_op = self_test_log.get("current_self_test_operation", {})
        op_value = current_op.get("value", 0)

        # Check for failed tests in history
        entries = self_test_log.get("entries")
        if not isinstance(entries, list):
            entries = self_test_log.get("table")
        if not isinstance(entries, list):
            entries = []
        if entries:
            # Check most recent entries for failures
            recent_failures = []
            for entry in entries[:5]:  # Check last 5 tests
                if self._nvme_selftest_entry_failed(entry):
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

        return deductions

    @staticmethod
    def _nvme_selftest_entry_failed(entry: dict) -> bool:
        """Return True when smartctl/nvme-cli reports a failed NVMe self-test entry."""
        result = entry.get("self_test_result")
        if isinstance(result, dict) and "value" in result:
            return HealthScoreCalculator._nvme_selftest_result_code_failed(result.get("value"))
        if "result" in entry:
            return HealthScoreCalculator._nvme_selftest_result_code_failed(entry.get("result"))
        result_string = str(entry.get("result_string") or entry.get("self_test_result_string") or "").lower()
        return "fail" in result_string

    @staticmethod
    def _nvme_selftest_result_code_failed(value: object) -> bool:
        try:
            return int(value or 0) == 1
        except (TypeError, ValueError):
            return "fail" in str(value).lower()

    def _check_scsi_metrics(self, device: dict) -> list[ScoreDeduction]:
        """Check SCSI-specific metrics."""
        deductions = []

        # Grown defects (SAS — same scaling as SATA reallocated/pending)
        grown_raw = device.get("grown_defects")
        if grown_raw is None:
            grown_raw = device.get("reallocated_sectors")
        grown_defects = int(grown_raw or 0)
        if self._use_hdd_sector_defect_curve(device):
            d = self._deduction_hdd_sector_defect(
                grown_defects,
                failure_threshold=self.config.maximum_grown_defects,
                reason="Grown defects",
                field="grown_defects",
            )
        else:
            d = self._deduction_ssd_style_defect_count(
                grown_defects,
                threshold=self.config.maximum_grown_defects,
                reason="Grown defects",
                field="grown_defects",
            )
        if d:
            deductions.append(d)

        # Uncorrected errors
        uncorrected = device.get("uncorrected_errors")
        if uncorrected is None:
            uncorrected = device.get("offline_uncorrectable_sectors")
        uncorrected = uncorrected or 0
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
