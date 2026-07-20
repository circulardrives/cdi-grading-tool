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

    # Score to Grade mapping (defaults; overridden from config when present)
    DEFAULT_GRADE_THRESHOLDS = [
        (90, "A", "Excellent"),
        (75, "B", "Good"),
        (60, "C", "Fair"),
        (40, "D", "Poor"),
        (0, "F", "Failed"),
    ]

    # Points deductions (defaults; overridden from config when present)
    DEFAULT_SMART_FAILURE_DEDUCTION = 50
    DEFAULT_PER_SECTOR_DEDUCTION = 5
    DEFAULT_THRESHOLD_EXCEEDED_DEDUCTION = 25
    DEFAULT_TEMP_WARNING_DEDUCTION = 5
    DEFAULT_TEMP_CRITICAL_DEDUCTION = 15

    def __init__(self):
        """Initialize the health score calculator."""
        self.config = get_config()
        self.GRADE_THRESHOLDS = self._load_grade_thresholds()
        self.SMART_FAILURE_DEDUCTION = self.config.smart_failure_deduction
        self.PER_SECTOR_DEDUCTION = self.config.per_sector_deduction
        self.THRESHOLD_EXCEEDED_DEDUCTION = self.config.threshold_exceeded_deduction
        self.TEMP_WARNING_DEDUCTION = self.config.temp_warning_deduction
        self.TEMP_CRITICAL_DEDUCTION = self.config.temp_critical_deduction

    def _load_grade_thresholds(self) -> list[tuple[int, str, str]]:
        """Build grade bands from config, falling back to CDI defaults."""
        bands = self.config.grade_score_bands
        if not bands:
            return list(self.DEFAULT_GRADE_THRESHOLDS)
        status_map = {"A": "Excellent", "B": "Good", "C": "Fair", "D": "Poor", "F": "Failed"}
        ordered = []
        for grade in ("A", "B", "C", "D", "F"):
            if grade in bands:
                ordered.append((int(bands[grade]), grade, status_map.get(grade, "")))
        return ordered or list(self.DEFAULT_GRADE_THRESHOLDS)

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

        # Uncorrectable / offline uncorrectable (canonical + legacy alias; score once)
        uncorrectable_raw = device.get("uncorrectable_errors")
        if uncorrectable_raw is None:
            uncorrectable_raw = device.get("offline_uncorrectable_sectors")
        uncorrectable = int(uncorrectable_raw or 0)
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

        # SSD Percentage Used Endurance (for ATA SSDs)
        # Check both ssd_percentage_used_endurance and percentage_used fields
        pct_used = device.get("ssd_percentage_used_endurance") or device.get("percentage_used")
        if pct_used is not None and pct_used >= 0:
            threshold = self.config.maximum_ssd_percentage_used
            warn_high = self.config.ssd_wear_warning_high
            warn_moderate = self.config.ssd_wear_warning_moderate
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
            elif pct_used > warn_high:
                deductions.append(
                    ScoreDeduction(
                        reason="High SSD percentage used",
                        points=self.config.ssd_wear_high_deduction,
                        severity="warning",
                        field="ssd_percentage_used_endurance",
                        value=pct_used,
                    )
                )
            elif pct_used > warn_moderate:
                deductions.append(
                    ScoreDeduction(
                        reason="Moderate SSD percentage used",
                        points=self.config.ssd_wear_moderate_deduction,
                        severity="info",
                        field="ssd_percentage_used_endurance",
                        value=pct_used,
                    )
                )

        # ATA SMART self-test history (same critical fail-gate as NVMe)
        deductions.extend(self._check_ata_scsi_selftest(device, protocol_label="ATA"))

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
        elif pct_used > self.config.ssd_wear_warning_high:
            deductions.append(
                ScoreDeduction(
                    reason="High percentage used",
                    points=self.config.ssd_wear_high_deduction,
                    severity="warning",
                    field="percentage_used",
                    value=pct_used,
                    threshold=threshold,
                )
            )
        elif pct_used > self.config.ssd_wear_warning_moderate:
            deductions.append(
                ScoreDeduction(
                    reason="Moderate percentage used",
                    points=self.config.ssd_wear_moderate_deduction,
                    severity="info",
                    field="percentage_used",
                    value=pct_used,
                    threshold=threshold,
                )
            )

        # Available spare — prefer drive AVSPT; YAML fallback is ~10%, not 97%
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

        # Critical Warning (NVMe Base Spec §5.2.12.1.3) — decode bits
        deductions.extend(self._check_nvme_critical_warning(device))

        # Endurance Group Critical Warning Summary (EGCWS)
        deductions.extend(self._check_nvme_egcws(device))

        # Lifetime composite-temp exposure (WCTT / CCTT)
        deductions.extend(self._check_nvme_temp_time(device))

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
        deductions.extend(self._check_nvme_selftest(device))

        # OCP C0h predictive-fail (skipped when log absent or disabled)
        deductions.extend(self._check_ocp_smart(device))

        return deductions

    # NVMe Critical Warning bit labels (Base Spec Figure 210)
    _NVME_CW_BITS: dict[int, str] = {
        0: "Available Spare Below Threshold (ASCBT)",
        1: "Temperature Threshold Condition (TTC)",
        2: "NVM Subsystem Degraded Reliability (NDR)",
        3: "All Media Read-Only (AMRO)",
        4: "Volatile Memory Backup Failed (VMBF)",
        5: "Persistent Memory Region Read-Only (PMRRO)",
        6: "Indeterminate Personality State (IPS)",
    }

    _NVME_EGCWS_BITS: dict[int, str] = {
        0: "Endurance Group Available Spare Below Threshold",
        2: "Endurance Group Degraded Reliability",
        3: "Endurance Group Read-Only",
    }

    def _check_nvme_critical_warning(self, device: dict) -> list[ScoreDeduction]:
        """Grade F on any Critical Warning bit; label which bits are set."""
        critical_warning = device.get("critical_warning", 0) or 0
        try:
            cw = int(critical_warning)
        except (TypeError, ValueError):
            return []
        if cw <= 0:
            return []

        labels = [name for bit, name in self._NVME_CW_BITS.items() if cw & (1 << bit)]
        unknown = cw & ~sum(1 << b for b in self._NVME_CW_BITS)
        if unknown:
            labels.append(f"reserved/unknown bits 0x{unknown:02x}")
        reason = "NVMe critical warning: " + (", ".join(labels) if labels else f"0x{cw:02x}")
        return [
            ScoreDeduction(
                reason=reason,
                points=self.SMART_FAILURE_DEDUCTION,
                severity="critical",
                field="critical_warning",
                value=cw,
            )
        ]

    def _check_nvme_egcws(self, device: dict) -> list[ScoreDeduction]:
        """Grade F when Endurance Group Critical Warning Summary has any bit set."""
        raw = device.get("endurance_group_critical_warning_summary")
        if raw is None:
            return []
        try:
            egcws = int(raw)
        except (TypeError, ValueError):
            return []
        if egcws <= 0:
            return []

        labels = [name for bit, name in self._NVME_EGCWS_BITS.items() if egcws & (1 << bit)]
        reason = "NVMe endurance group critical warning: " + (
            ", ".join(labels) if labels else f"0x{egcws:02x}"
        )
        return [
            ScoreDeduction(
                reason=reason,
                points=self.SMART_FAILURE_DEDUCTION,
                severity="critical",
                field="endurance_group_critical_warning_summary",
                value=egcws,
            )
        ]

    def _check_nvme_temp_time(self, device: dict) -> list[ScoreDeduction]:
        """Score lifetime WCTT / CCTT minutes from SMART health log."""
        deductions: list[ScoreDeduction] = []

        cctt = device.get("critical_comp_time")
        try:
            cctt_i = int(cctt) if cctt is not None else None
        except (TypeError, ValueError):
            cctt_i = None
        if cctt_i is not None and cctt_i > self.config.nvme_cctt_critical_minutes:
            deductions.append(
                ScoreDeduction(
                    reason="Critical composite temperature time (CCTT) > 0",
                    points=self.TEMP_CRITICAL_DEDUCTION,
                    severity="critical",
                    field="critical_comp_time",
                    value=cctt_i,
                    threshold=self.config.nvme_cctt_critical_minutes,
                )
            )

        wctt = device.get("warning_temp_time")
        try:
            wctt_i = int(wctt) if wctt is not None else None
        except (TypeError, ValueError):
            wctt_i = None
        if wctt_i is not None and wctt_i > self.config.nvme_wctt_warning_minutes:
            deductions.append(
                ScoreDeduction(
                    reason="Warning composite temperature time (WCTT) elevated",
                    points=self.TEMP_WARNING_DEDUCTION,
                    severity="warning",
                    field="warning_temp_time",
                    value=wctt_i,
                    threshold=self.config.nvme_wctt_warning_minutes,
                )
            )

        return deductions

    def _check_ocp_smart(self, device: dict) -> list[ScoreDeduction]:
        """
        OCP C0h predictive-fail algorithm (v1, DSSD v2.7 field semantics).

        See docs/NVME_HEALTH_POLICY.md. Skipped when C0h is absent or disabled.
        """
        if not self.config.ocp_scoring_enabled:
            return []

        ocp = device.get("ocp_smart_log")
        if not isinstance(ocp, dict) or not ocp:
            return []

        from cdi_health.classes.ocp_smart import ocp_get

        deductions: list[ScoreDeduction] = []

        # Capacitor Health (SMART-19): FFFFh = no PLP; 100 = factory pass margin
        cap = ocp_get(ocp, "Capacitor health", "capacitor_health")
        if cap is not None and cap != 0xFFFF and cap < self.config.ocp_capacitor_health_min:
            deductions.append(
                ScoreDeduction(
                    reason="OCP capacitor health below factory pass margin",
                    points=self.SMART_FAILURE_DEDUCTION,
                    severity="critical",
                    field="ocp_capacitor_health",
                    value=cap,
                    threshold=self.config.ocp_capacitor_health_min,
                )
            )

        # Uncorrectable read errors (SMART-6)
        unc = ocp_get(ocp, "Uncorrectable read error count", "uncorrectable_read_error_count")
        if unc is not None and unc > 0:
            deductions.append(
                ScoreDeduction(
                    reason="OCP uncorrectable read errors detected",
                    points=self.SMART_FAILURE_DEDUCTION,
                    severity="critical",
                    field="ocp_uncorrectable_read_error_count",
                    value=unc,
                    threshold=0,
                )
            )

        # End-to-end: uncorrected = detected - corrected (SMART-8)
        e2e_det = ocp_get(ocp, "End to end detected errors", "end_to_end_detected_errors")
        e2e_cor = ocp_get(ocp, "End to end corrected errors", "end_to_end_corrected_errors") or 0
        if e2e_det is not None and e2e_det > e2e_cor:
            deductions.append(
                ScoreDeduction(
                    reason="OCP end-to-end uncorrected errors",
                    points=self.SMART_FAILURE_DEDUCTION,
                    severity="critical",
                    field="ocp_end_to_end_errors",
                    value=e2e_det - e2e_cor,
                    threshold=0,
                )
            )

        # Bad user NAND normalized (SMART-3); factory start = 100; 0xFFFF = invalid
        bad_norm = ocp_get(ocp, "Bad user nand blocks - Normalized", "bad_user_nand_blocks_normalized")
        if bad_norm is not None and bad_norm != 0xFFFF:
            if bad_norm < self.config.ocp_bad_user_nand_critical:
                deductions.append(
                    ScoreDeduction(
                        reason="OCP bad user NAND normalized critically low",
                        points=self.THRESHOLD_EXCEEDED_DEDUCTION,
                        severity="critical",
                        field="ocp_bad_user_nand_normalized",
                        value=bad_norm,
                        threshold=self.config.ocp_bad_user_nand_critical,
                    )
                )
            elif bad_norm < self.config.ocp_bad_user_nand_warning:
                deductions.append(
                    ScoreDeduction(
                        reason="OCP bad user NAND normalized low",
                        points=self.TEMP_WARNING_DEDUCTION,
                        severity="warning",
                        field="ocp_bad_user_nand_normalized",
                        value=bad_norm,
                        threshold=self.config.ocp_bad_user_nand_warning,
                    )
                )

        # System data % used (SMART-9): 100 = may no longer function reliably
        sys_used = ocp_get(ocp, "System data percent used", "system_data_percent_used")
        if sys_used is not None:
            if sys_used >= 100:
                deductions.append(
                    ScoreDeduction(
                        reason="OCP system data percent used at/above 100",
                        points=self.THRESHOLD_EXCEEDED_DEDUCTION,
                        severity="critical",
                        field="ocp_system_data_percent_used",
                        value=sys_used,
                        threshold=100,
                    )
                )
            elif sys_used >= self.config.ocp_system_data_used_warning:
                deductions.append(
                    ScoreDeduction(
                        reason="OCP system data percent used elevated",
                        points=self.TEMP_WARNING_DEDUCTION,
                        severity="warning",
                        field="ocp_system_data_percent_used",
                        value=sys_used,
                        threshold=self.config.ocp_system_data_used_warning,
                    )
                )

        # Incomplete shutdowns (SMART-15) — warning tier
        incomplete = ocp_get(ocp, "Incomplete shutdowns", "incomplete_shutdowns")
        if incomplete is not None and incomplete >= self.config.ocp_incomplete_shutdowns_warning:
            deductions.append(
                ScoreDeduction(
                    reason="OCP incomplete shutdowns elevated",
                    points=self.TEMP_WARNING_DEDUCTION,
                    severity="warning",
                    field="ocp_incomplete_shutdowns",
                    value=incomplete,
                    threshold=self.config.ocp_incomplete_shutdowns_warning,
                )
            )

        # Thermal throttling (SMART-12) — warning only
        throttle_events = ocp_get(
            ocp, "Number of Thermal throttling events", "number_of_thermal_throttling_events"
        )
        throttle_status = ocp_get(ocp, "Current throttling status", "current_throttling_status")
        if throttle_status is not None and throttle_status >= 2:
            deductions.append(
                ScoreDeduction(
                    reason="OCP thermal throttling active (level ≥ 2)",
                    points=self.TEMP_WARNING_DEDUCTION,
                    severity="warning",
                    field="ocp_current_throttling_status",
                    value=throttle_status,
                    threshold=2,
                )
            )
        elif (
            throttle_events is not None
            and throttle_events >= self.config.ocp_thermal_throttle_events_warning
        ):
            deductions.append(
                ScoreDeduction(
                    reason="OCP thermal throttling events elevated",
                    points=self.TEMP_WARNING_DEDUCTION,
                    severity="warning",
                    field="ocp_thermal_throttling_events",
                    value=throttle_events,
                    threshold=self.config.ocp_thermal_throttle_events_warning,
                )
            )

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

    def _check_ata_scsi_selftest(self, device: dict, *, protocol_label: str) -> list[ScoreDeduction]:
        """
        Deduct for failed ATA/SCSI SMART self-tests in recent history.

        Uses the same critical deduction as NVMe so a failed self-test is Grade F.
        Only the most recent 5 entries are considered (aligns with NVMe policy).
        """
        entries = device.get("smart_self_tests")
        if not isinstance(entries, list) or not entries:
            return []

        for entry in entries[:5]:
            if not isinstance(entry, dict):
                continue
            if self._ata_scsi_selftest_entry_failed(entry):
                return [
                    ScoreDeduction(
                        reason=f"Failed {protocol_label} self-test - Drive is failing",
                        points=self.SMART_FAILURE_DEDUCTION,
                        severity="critical",
                        field="smart_self_tests",
                        value="Failed",
                    )
                ]
        return []

    @staticmethod
    def _ata_scsi_selftest_entry_failed(entry: dict) -> bool:
        """True when an ATA/SCSI self-test entry reports a completed failure."""
        status = entry.get("status")
        if isinstance(status, dict):
            if "passed" in status:
                # Explicit pass/fail; ignore in-progress / aborted-by-host (passed absent or None)
                passed = status.get("passed")
                if passed is None:
                    return False
                return passed is False
            status_string = str(status.get("string") or "").lower()
            if any(token in status_string for token in ("in progress", "aborted", "interrupted")):
                return False
            return "fail" in status_string or "error" in status_string

        # SCSI dumps sometimes use flat result/string fields
        for key in ("result", "self_test_result", "result_string"):
            value = entry.get(key)
            if value is None:
                continue
            if isinstance(value, bool):
                return value is False
            text = str(value).lower()
            if any(token in text for token in ("in progress", "aborted", "interrupted")):
                return False
            if "fail" in text or "error" in text:
                return True
        return False

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

        # Uncorrected errors (canonical uncorrectable_errors + legacy aliases)
        uncorrected = device.get("uncorrected_errors")
        if uncorrected is None:
            uncorrected = device.get("uncorrectable_errors")
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

        # SCSI self-test history (same critical fail-gate as NVMe/ATA)
        deductions.extend(self._check_ata_scsi_selftest(device, protocol_label="SCSI"))

        return deductions

    @staticmethod
    def _coerce_temp_celsius(value) -> int | None:
        """Coerce a temperature field to int °C; None when missing/non-numeric."""
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value.strip())
        return None

    def _resolve_temperature_thresholds(self, device: dict) -> tuple[int | None, int | None]:
        """
        Resolve warning / critical °C thresholds for current-temp scoring.

        Prefer drive-reported limits (NVMe WCTEMP/CCTEMP, ATA specified max,
        SCSI drive_trip). YAML 55/60 is an ATA/SCSI fallback only.

        For NVMe without WCTEMP/CCTEMP, return (None, None) so current-temp
        does not use the YAML ceiling — CW bit 1 + WCTT/CCTT are the gates.
        """
        drive_warning = self._coerce_temp_celsius(device.get("warning_temperature"))
        drive_max = self._coerce_temp_celsius(device.get("maximum_temperature"))
        protocol = str(device.get("transport_protocol", "")).upper()

        if drive_warning is None and drive_max is None and protocol == "NVME":
            return None, None

        warning_temp = drive_warning if drive_warning is not None else self.config.warning_temperature
        max_temp = drive_max if drive_max is not None else self.config.maximum_operating_temperature
        if warning_temp >= max_temp:
            # Mixed sources (e.g. drive critical only) — keep a warning band below critical.
            warning_temp = max(max_temp - 5, 0)
        return warning_temp, max_temp

    def _check_temperature(self, device: dict) -> list[ScoreDeduction]:
        """Check temperature metrics."""
        deductions = []

        # Coerce to int; skip scoring for missing or non-numeric values
        # (collection/mock data may carry strings like "Not Reported").
        temp = self._coerce_temp_celsius(device.get("current_temperature"))
        if temp is None:
            # Still evaluate historical excursion if present
            pass
        else:
            warning_temp, max_temp = self._resolve_temperature_thresholds(device)
            if max_temp is not None and temp > max_temp:
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
            elif warning_temp is not None and temp > warning_temp:
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

        # Historical excursion beyond the drive's own specified maximum
        # operating temperature (previously a scan-time hard fail-gate in the
        # protocol handlers; kept critical here to preserve that behavior).
        highest = self._coerce_temp_celsius(device.get("highest_temperature"))
        spec_max = self._coerce_temp_celsius(device.get("maximum_temperature"))
        if highest is not None and spec_max is not None and highest > spec_max:
            deductions.append(
                ScoreDeduction(
                    reason="Highest recorded temperature exceeded specified maximum",
                    points=self.TEMP_CRITICAL_DEDUCTION,
                    severity="critical",
                    field="highest_temperature",
                    value=highest,
                    threshold=spec_max,
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
