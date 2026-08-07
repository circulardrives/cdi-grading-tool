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
Grading explainability helpers for CDI Health.

Builds human-readable certification rationale and terminal detail views from
existing ``HealthScore`` / ``ScoreDeduction`` data — no parallel scoring.
"""

from __future__ import annotations

from typing import Any

from cdi_health.classes.colors import Colors, Symbols
from cdi_health.classes.scoring import HealthScore, HealthScoreCalculator, ScoreDeduction


def deduction_to_dict(deduction: ScoreDeduction) -> dict[str, Any]:
    """Serialize a single score deduction to a stable dict."""
    return {
        "reason": deduction.reason,
        "points": deduction.points,
        "severity": deduction.severity,
        "field": deduction.field,
        "value": deduction.value,
        "threshold": deduction.threshold,
        "attribute_grade": deduction.attribute_grade,
    }


def deductions_to_dicts(deductions: list[ScoreDeduction]) -> list[dict[str, Any]]:
    """Serialize deductions to a stable list of dicts."""
    return [deduction_to_dict(d) for d in deductions]


def _is_failed_selftest(deduction: ScoreDeduction) -> bool:
    reason = deduction.reason.lower()
    return "failed" in reason and "self-test" in reason


def certification_blockers(score: HealthScore) -> list[str]:
    """
    Return stable, human-readable reasons certification was blocked.

    Mirrors ``HealthScoreCalculator.calculate`` certification rules:
    grade A/B required, no critical deductions, no failed self-test.
    """
    if score.is_certified:
        return []

    blockers: list[str] = []
    if score.grade not in ("A", "B"):
        blockers.append(f"grade is {score.grade} (certification requires A or B)")

    seen: set[str] = set()
    for deduction in score.deductions:
        if deduction.severity == "critical":
            msg = f"critical deduction: {deduction.reason}"
        elif _is_failed_selftest(deduction):
            msg = f"failed self-test: {deduction.reason}"
        else:
            continue
        if msg not in seen:
            blockers.append(msg)
            seen.add(msg)

    return blockers


def certification_rationale(score: HealthScore) -> str:
    """Short explanation of why the drive is or is not CDI-certified."""
    if score.is_certified:
        return f"Certified because grade {score.grade} ({score.status}) and no critical deductions."

    blockers = certification_blockers(score)
    if blockers:
        return "Not certified because " + "; ".join(blockers) + "."
    return "Not certified."


def explanation_fields(score: HealthScore) -> dict[str, Any]:
    """
    Stable explainability payload derived from an existing HealthScore.

    Suitable for JSON/YAML/API enrichment alongside ``HealthScore.to_dict()``.
    """
    points_deducted = sum(d.points for d in score.deductions)
    return {
        "certification_rationale": certification_rationale(score),
        "certification_blockers": certification_blockers(score),
        "points_deducted": points_deducted,
        "grading_explanation": {
            "score": score.score,
            "grade": score.grade,
            "status": score.status,
            "is_certified": score.is_certified,
            "certification_rationale": certification_rationale(score),
            "certification_blockers": certification_blockers(score),
            "points_deducted": points_deducted,
            "deductions": deductions_to_dicts(score.deductions),
        },
    }


def attach_explanation(device: dict[str, Any], score: HealthScore | None = None) -> dict[str, Any]:
    """
    Return a copy of ``device`` enriched with score + explainability fields.

    Reuses ``HealthScoreCalculator`` when ``score`` is not provided.
    """
    if score is None:
        score = HealthScoreCalculator().calculate(device)

    enriched = dict(device)
    enriched.update(score.to_dict())
    enriched.update(explanation_fields(score))
    return enriched


def _fmt_cell(value: Any, width: int) -> str:
    text = "-" if value is None else str(value)
    if len(text) > width:
        text = text[: width - 1] + "…"
    return text.ljust(width)


def _color_severity(severity: str) -> str:
    color = Colors.severity_color(severity)
    return Colors.colorize(severity, color)


def format_device_explanation(device: dict[str, Any], score: HealthScore | None = None) -> str:
    """Format a single device grading explanation for the terminal."""
    if score is None:
        score = HealthScoreCalculator().calculate(device)

    dut = device.get("dut") or device.get("device") or "—"
    model = device.get("model_number") or "—"
    serial = device.get("serial_number") or "—"
    certified = "Yes" if score.is_certified else "No"
    certified_display = Colors.green(certified) if score.is_certified else Colors.red(certified)
    grade_display = Colors.colorize(score.grade, Colors.grade_color(score.grade))

    lines: list[str] = [
        Colors.bold(f"Device: {dut}"),
        f"  Model:  {model}",
        f"  Serial: {serial}",
        "",
        f"  Grade: {grade_display}    Score: {score.score}    Status: {score.status}    Certified: {certified_display}",
        f"  Certification: {certification_rationale(score)}",
        "",
    ]

    if not score.deductions:
        lines.append("  Deductions: none")
    else:
        # Only non-band warning/info points are subtracted from the band base (#119).
        arithmetic_points = sum(
            d.points for d in score.deductions if d.attribute_grade is None and d.severity in ("info", "warning")
        )
        band_n = sum(1 for d in score.deductions if d.attribute_grade is not None)
        summary_bits = [f"{len(score.deductions)} items"]
        if band_n:
            summary_bits.append(f"{band_n} graded attributes")
        if arithmetic_points:
            summary_bits.append(f"{arithmetic_points} warning points")
        lines.append(f"  Deductions ({'; '.join(summary_bits)}):")
        header = (
            f"    {_fmt_cell('Severity', 10)} {_fmt_cell('Impact', 7)} "
            f"{_fmt_cell('Field', 24)} {_fmt_cell('Value', 10)} "
            f"{_fmt_cell('Threshold', 10)} Reason"
        )
        lines.append(Colors.dim(header))
        for deduction in score.deductions:
            sev_colored = _color_severity(deduction.severity) + (" " * max(0, 10 - len(deduction.severity)))
            if deduction.attribute_grade is not None:
                impact = f"grade {deduction.attribute_grade}"
            else:
                impact = f"-{deduction.points}"
            lines.append(
                f"    {sev_colored} {_fmt_cell(impact, 7)} "
                f"{_fmt_cell(deduction.field, 24)} {_fmt_cell(deduction.value, 10)} "
                f"{_fmt_cell(deduction.threshold, 10)} {deduction.reason}"
            )

    blockers = certification_blockers(score)
    if blockers and not score.is_certified:
        lines.append("")
        lines.append("  Certification blockers:")
        for blocker in blockers:
            lines.append(f"    {Symbols.CROSS} {blocker}")

    return "\n".join(lines)


def format_explanations(devices: list[dict[str, Any]]) -> str:
    """Format grading explanations for one or more devices."""
    if not devices:
        return "No devices found."

    calculator = HealthScoreCalculator()
    sections: list[str] = [
        Colors.bold("CDI Health — Grading Explainability"),
        Colors.dim("Score and certification breakdown from the health scoring engine."),
        "",
    ]

    for index, device in enumerate(devices):
        score = calculator.calculate(device)
        sections.append(format_device_explanation(device, score))
        if index < len(devices) - 1:
            sections.append("")
            sections.append(Colors.dim("─" * 72))
            sections.append("")

    return "\n".join(sections)


class ExplainFormatter:
    """Terminal formatter for ``cdi-health scan --explain``."""

    def __init__(self) -> None:
        self.calculator = HealthScoreCalculator()

    def format(self, devices: list[dict]) -> str:
        return format_explanations(devices)
