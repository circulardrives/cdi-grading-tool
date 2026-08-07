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
Revert Drive Grading Standard v2.0 output-schema support.

Implements the §13 per-drive output fields (structured attribute grades,
standardized fail reason codes, tri-state certification, recommended use,
drive class, per-drive scan timestamp, standard version tag) and the §15
edge-case fields (UNGRADED status, warning flags, duplicate-serial
detection) for the JSON/CSV/HTML/YAML outputs.

Several §13 fields depend on values the scoring engine does not compute
yet (age_cap_grade, defect_grade, per-attribute grades, multi-factor
degradation, tri-state certification). Those are read from the scoring
result with ``getattr`` and default to ``None`` / a derived fallback so
this module keeps working unchanged once the scoring engine lands them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

REVERT_STANDARD_VERSION = "2.0"

# Grading status (§15)
STATUS_GRADED = "GRADED"
STATUS_UNGRADED = "UNGRADED"

# Grade string used in output grade fields for ungraded drives
UNGRADED_GRADE = "UNGRADED"

# Warning flags (§15)
FLAG_SMART_RESET_SUSPECTED = "SMART_RESET_SUSPECTED"  # §15.1
FLAG_DUPLICATE_SERIAL = "DUPLICATE_SERIAL"  # §15.7

# Ungraded reason codes (§4.1, §15.5, §15.6)
UNGRADED_SECURITY_LOCKED = "SECURITY_LOCKED"
UNGRADED_SMART_UNREADABLE = "SMART_UNREADABLE"
UNGRADED_USB_PASSTHROUGH = "USB_PASSTHROUGH_FAILURE"
UNGRADED_RAID_PASSTHROUGH = "RAID_PASSTHROUGH_FAILURE"
UNGRADED_DEVICE_OPEN_FAILURE = "DEVICE_OPEN_FAILURE"
UNGRADED_DEVICE_TIMEOUT = "DEVICE_TIMEOUT"
UNGRADED_UNSUPPORTED_PROTOCOL = "UNSUPPORTED_PROTOCOL"

# Recommended use per grade (§2). Only the C-grade wording is quoted in the
# standard excerpts available here; the others follow the same tiering.
_RECOMMENDED_USE = {
    "A": "Primary/Production",
    "B": "General purpose",
    "C": "Non-critical/Archival",
    "D": "Non-critical/Archival (Advisory)",
    "F": "Do not reuse - destroy/recycle",
    UNGRADED_GRADE: "Manual review required",
    "U": "Manual review required",
}

# Scoring deduction field -> standardized fail reason code (§13)
_FAIL_CODE_BY_FIELD = {
    "smart_status": "F-SMART-FAIL",
    "state": "F-NO-RESPONSE",
    "grown_defects": "F-GROWN-DEFECTS",
    "reallocated_sectors": "F-REALLOCATED-SECTORS",
    "pending_sectors": "F-PENDING-SECTORS",
    "uncorrectable_errors": "F-UNCORRECTED-ERRORS",
    "uncorrected_errors": "F-UNCORRECTED-ERRORS",
    "smart_self_tests": "F-SELF-TEST",
    "nvme_self_test": "F-SELF-TEST",
    "critical_warning": "F-NVME-CRITICAL-WARNING",
    "endurance_group_critical_warning_summary": "F-NVME-CRITICAL-WARNING",
    "media_errors": "F-MEDIA-ERRORS",
    "current_temperature": "F-TEMPERATURE",
    "highest_temperature": "F-TEMPERATURE",
    "critical_comp_time": "F-TEMPERATURE",
    "ssd_percentage_used_endurance": "F-ENDURANCE",
    "percentage_used": "F-ENDURANCE",
    "available_spare": "F-SPARE-BLOCKS",
}


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return None


def _field_fail_code(field: str | None) -> str:
    code = _FAIL_CODE_BY_FIELD.get(field or "")
    if code:
        return code
    if field:
        return "F-" + field.upper().replace("_", "-")
    return "F-UNSPECIFIED"


def fail_reason_codes(deductions: list | None) -> list[str]:
    """Standardized §13 fail reason codes for grade-affecting deductions."""
    codes: list[str] = []
    for d in deductions or []:
        severity = getattr(d, "severity", None)
        field = getattr(d, "field", None)
        if isinstance(d, dict):
            severity = d.get("severity")
            field = d.get("field")
        if str(severity or "").lower() != "critical":
            continue
        code = _field_fail_code(field)
        if code not in codes:
            codes.append(code)
    return codes


def recommended_use(grade: str | None) -> str | None:
    """Recommended-use disposition per Revert Standard §2."""
    if not grade:
        return None
    return _RECOMMENDED_USE.get(str(grade).upper())


def drive_class(device: dict, score: Any = None) -> str | None:
    """
    "consumer" / "enterprise" classification used for §5 age-cap table
    selection. Prefers the scoring engine's value, then an explicit device
    field, otherwise derives from transport/form factor.
    """
    for candidate in (getattr(score, "drive_class", None), device.get("drive_class")):
        if candidate in ("consumer", "enterprise"):
            return candidate

    protocol = str(device.get("transport_protocol") or "").upper()
    if protocol == "SCSI":
        return "enterprise"
    if protocol == "ATA":
        return "consumer"
    if protocol == "NVME":
        form_factor = str(device.get("form_factor") or "").lower()
        if any(token in form_factor for token in ("m.2", "msata")):
            return "consumer"
        return "enterprise"
    return None


def _normalize_tri_state(value: Any) -> str | None:
    """Coerce a scoring-provided certification value into "true"/"Advisory"/"false"."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).strip()
    if not text:
        return None
    if text.lower() == "advisory":
        return "Advisory"
    if text.lower() in ("true", "yes", "certified"):
        return "true"
    if text.lower() in ("false", "no", "not certified"):
        return "false"
    return text


def revert_certified(score: Any, device: dict) -> str:
    """
    Tri-state certification per §12.7: "true" (A/B/C), "Advisory" (D),
    "false" (F). Prefers ``score.certification`` / ``revert_certified``;
    falls back to binary ``is_certified`` when the tri-state is absent.
    """
    for candidate in (
        getattr(score, "certification", None),
        getattr(score, "revert_certified", None),
        device.get("certification"),
        device.get("revert_certified"),
    ):
        explicit = _normalize_tri_state(candidate)
        if explicit is not None:
            return explicit

    is_certified = getattr(score, "is_certified", None)
    if is_certified is None:
        is_certified = bool(device.get("is_certified"))
    return "true" if is_certified else "false"


def revert_eligible(score: Any, device: dict) -> bool:
    """Boolean resale eligibility (§13). Grade F is never eligible."""
    explicit = getattr(score, "revert_eligible", None)
    if explicit is None:
        explicit = device.get("revert_eligible")
    if explicit is not None:
        return bool(explicit)
    grade = getattr(score, "grade", None) or device.get("health_grade")
    return grade is not None and str(grade).upper() != "F"


def attribute_grades(score: Any, device: dict) -> dict[str, dict[str, Any]]:
    """
    Structured §13 map of attribute -> {value, grade}.

    Prefers the scoring engine's per-attribute grade map when present;
    otherwise builds the structure from the score deductions with
    ``grade=None`` (per-attribute grades are pending in the scoring engine).
    """
    explicit = getattr(score, "attribute_grades", None)
    if explicit is None:
        explicit = device.get("attribute_grades")
    if isinstance(explicit, dict) and explicit:
        return explicit

    out: dict[str, dict[str, Any]] = {}
    for d in getattr(score, "deductions", None) or []:
        field = getattr(d, "field", None)
        value = getattr(d, "value", None)
        threshold = getattr(d, "threshold", None)
        if isinstance(d, dict):
            field = d.get("field")
            value = d.get("value")
            threshold = d.get("threshold")
        if not field:
            continue
        out[str(field)] = {"value": value, "grade": None, "threshold": threshold}
    return out


def ungraded_reasons(device: dict) -> list[str]:
    """Reasons a drive must be reported UNGRADED instead of graded (§15)."""
    reasons: list[str] = []
    for reason in device.get("ungraded_reasons") or []:
        if reason and reason not in reasons:
            reasons.append(str(reason))

    if device.get("security_locked") and UNGRADED_SECURITY_LOCKED not in reasons:
        reasons.append(UNGRADED_SECURITY_LOCKED)
    if device.get("smart_data_readable") is False and UNGRADED_SMART_UNREADABLE not in reasons:
        reasons.append(UNGRADED_SMART_UNREADABLE)
    if device.get("grading_status") == STATUS_UNGRADED and not reasons:
        reasons.append(UNGRADED_DEVICE_OPEN_FAILURE)
    return reasons


def is_ungraded(device: dict) -> bool:
    """True when a drive must never receive a letter grade in the output."""
    return device.get("grading_status") == STATUS_UNGRADED or bool(ungraded_reasons(device))


def warning_flags(device: dict) -> list[str]:
    """§15 warning flags (non-fatal anomalies that must surface in output)."""
    flags: list[str] = []
    for flag in device.get("warning_flags") or []:
        if flag and flag not in flags:
            flags.append(str(flag))

    if _smart_reset_suspected(device) and FLAG_SMART_RESET_SUSPECTED not in flags:
        flags.append(FLAG_SMART_RESET_SUSPECTED)
    return flags


def _smart_reset_suspected(device: dict) -> bool:
    """
    §15.1 heuristic: near-zero power-on hours combined with evidence of a
    long service life (high power-cycle count or existing media defects)
    suggests the SMART counters were reset.
    """
    poh = _int_or_none(device.get("power_on_hours"))
    if poh is None or poh >= 100:
        return False

    power_cycles = _int_or_none(device.get("power_cycle_count")) or 0
    reallocated = _int_or_none(device.get("reallocated_sectors")) or 0
    grown = _int_or_none(device.get("grown_defects")) or 0
    pending = _int_or_none(device.get("pending_sectors")) or 0
    uncorrectable = _int_or_none(device.get("uncorrectable_errors")) or 0

    if power_cycles >= 100:
        return True
    return max(reallocated, grown, pending, uncorrectable) > 0


def revert_fields(device: dict, score: Any = None) -> dict[str, Any]:
    """
    Build the full Revert Standard §13/§15 per-drive output payload.

    ``device`` is the (possibly already score-enriched) device dict;
    ``score`` is the ``HealthScore`` result when available. Returned keys
    are merged into the per-drive record for every output format. When the
    drive is UNGRADED, the payload also overrides the grade/score fields so
    no output format silently assigns a grade.
    """
    reasons = ungraded_reasons(device)
    ungraded = bool(reasons)

    grade = getattr(score, "grade", None) or device.get("health_grade")
    deductions = getattr(score, "deductions", None)
    if deductions is None:
        deductions = device.get("health_deductions") or device.get("deductions")

    final_grade = UNGRADED_GRADE if ungraded else grade
    # For UNGRADED rows, surface the §15 reason codes in fail_reason_codes too
    # so JSON/CSV consumers that only look at fail codes still see why (#117/#122).
    codes = list(reasons) if ungraded else fail_reason_codes(deductions)
    fields: dict[str, Any] = {
        "revert_standard_version": REVERT_STANDARD_VERSION,
        "scan_timestamp": device.get("scan_timestamp") or _now_utc_iso(),
        "drive_class": drive_class(device, score),
        "grading_status": STATUS_UNGRADED if ungraded else STATUS_GRADED,
        "ungraded_reasons": reasons,
        "warning_flags": warning_flags(device),
        "attribute_grades": {} if ungraded else attribute_grades(score, device),
        # Stage 2 / Stage 3 intermediate grades and §12.5 multi-factor flag:
        # populated by the scoring engine when available, otherwise None.
        "age_cap_grade": None if ungraded else getattr(score, "age_cap_grade", None),
        "defect_grade": None if ungraded else getattr(score, "defect_grade", None),
        "multi_factor_applied": None if ungraded else getattr(score, "multi_factor_applied", None),
        "final_grade": final_grade,
        "fail_reason_codes": codes,
        "revert_eligible": False if ungraded else revert_eligible(score, device),
        "revert_certified": "false" if ungraded else revert_certified(score, device),
        "recommended_use": recommended_use(final_grade),
    }

    if ungraded:
        fields.update(
            {
                "health_grade": UNGRADED_GRADE,
                "health_status": "Ungraded",
                "health_score": None,
                "is_certified": False,
                "certification_rationale": (
                    "Not graded: " + "; ".join(reasons) + ". Drive requires manual review before disposition."
                ),
            }
        )

    return fields


def flag_duplicate_serials(devices: list[dict]) -> None:
    """
    §15.7: flag every record whose serial number appears more than once in
    the same scan with ``DUPLICATE_SERIAL`` (in place, on enriched dicts).
    """
    counts: dict[str, int] = {}
    for device in devices:
        serial = _usable_serial(device)
        if serial:
            counts[serial] = counts.get(serial, 0) + 1

    for device in devices:
        serial = _usable_serial(device)
        if not serial or counts.get(serial, 0) < 2:
            continue
        flags = list(device.get("warning_flags") or [])
        if FLAG_DUPLICATE_SERIAL not in flags:
            flags.append(FLAG_DUPLICATE_SERIAL)
        device["warning_flags"] = flags


def _usable_serial(device: dict) -> str | None:
    serial = str(device.get("serial_number") or "").strip()
    if not serial or serial.lower() in ("not reported", "unknown", "-", "—"):
        return None
    return serial


def csv_cell(value: Any) -> str:
    """Flatten a §13 value (list/dict/bool/None) for a CSV cell."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return " | ".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str) if value else ""
    return str(value)
