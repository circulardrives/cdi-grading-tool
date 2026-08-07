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

"""Helpers for Revert Drive Grading Standard v2.0 regression fixtures (#124)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cdi_health.classes.mock import create_mock_device
from cdi_health.classes.scoring import HealthScore, calculate_health_score

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "revert_standard"

GRADE_ORDER: tuple[str, ...] = ("A", "B", "C", "D", "F")
_GRADE_RANK = {g: i for i, g in enumerate(GRADE_ORDER)}

# Sector-count defect bands (§6 grown/reallocated/pending/offline; §8 grown)
DEFECT_BANDS = {"A": 0, "B": 9, "C": 50, "D": 100}
# Error-count bands (§6 reported uncorrect/CRC/timeout; §8 uncorrected R+W)
ERROR_BANDS = {"A": 0, "B": 5, "C": 25, "D": 100}

SELFTEST_RECENT_POH_WINDOW = 1000

# Fixtures whose Revert Standard expected grade is pinned but the tool's
# graduated wear scoring is still incomplete (#116/#115/#121).
PENDING_GRADUATED_SCORING: frozenset[str] = frozenset(
    {
        "ata_ssd_midlife_wear",
        "ata_ssd_end_of_life_wear",
    }
)


def worst_grade(*grades: str) -> str:
    """Return the worst (lowest) of the given letter grades."""
    return max(grades, key=lambda g: _GRADE_RANK.get(g, 0))


def band_grade(value: int, bands: dict[str, int]) -> str:
    """Grade a raw count against per-grade maximums (above D max → F)."""
    for grade in ("A", "B", "C", "D"):
        if value <= bands[grade]:
            return grade
    return "F"


def certification_for_grade(grade: str) -> str:
    """§12.7 tri-state certification."""
    if grade in ("A", "B", "C"):
        return "true"
    if grade == "D":
        return "Advisory"
    return "false"


def list_fixture_paths() -> list[Path]:
    """Every smartctl-shaped JSON fixture in the revert_standard directory."""
    return sorted(p for p in FIXTURE_DIR.glob("*.json") if p.is_file())


def load_fixture(path: Path) -> dict[str, Any]:
    """Load one fixture JSON payload."""
    return json.loads(path.read_text(encoding="utf-8"))


def device_dict_from_fixture(path: Path | None = None, *, payload: dict | None = None) -> dict:
    """
    Adapt a smartctl-shaped fixture into the Device ``to_dict`` shape the
    public scorer expects (via ``create_mock_device`` + protocol parsers).
    """
    if path is not None:
        device = create_mock_device(json_file=path)
    elif payload is not None:
        device = create_mock_device(mock_data=payload)
    else:
        raise ValueError("path or payload is required")
    return device.to_dict(pop=True)


def grade_fixture_with_tool(path: Path) -> HealthScore:
    """Run the tool's public grading API against a fixture."""
    return calculate_health_score(device_dict_from_fixture(path))


def _ata_attr_raw(payload: dict, attr_id: int) -> int:
    table = (payload.get("ata_smart_attributes") or {}).get("table") or []
    for entry in table:
        if entry.get("id") == attr_id:
            raw = entry.get("raw") or {}
            try:
                return int(raw.get("value", 0) or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def _poh(payload: dict) -> int:
    pot = payload.get("power_on_time") or {}
    try:
        return int(pot.get("hours", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _protocol(payload: dict) -> str:
    device = payload.get("device") or {}
    proto = str(device.get("protocol") or "").upper()
    if proto in ("ATA", "SCSI", "NVME"):
        return proto
    transport = payload.get("transport_protocol")
    if isinstance(transport, dict):
        name = str(transport.get("name") or "").upper()
        if name in ("SAS", "SCSI"):
            return "SCSI"
        if name == "NVME":
            return "NVME"
    return proto or "UNKNOWN"


def _is_ssd(payload: dict) -> bool:
    if payload.get("nvme_smart_health_information_log") is not None:
        return True
    rotation = payload.get("rotation_rate")
    if rotation == 0:
        return True
    return bool(payload.get("ata_device_statistics"))


def _ssd_pct_used(payload: dict) -> int | None:
    nvme = payload.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict) and "percentage_used" in nvme:
        try:
            return int(nvme["percentage_used"])
        except (TypeError, ValueError):
            return None
    for page in (payload.get("ata_device_statistics") or {}).get("pages") or []:
        if page.get("name") != "Solid State Device Statistics":
            continue
        for entry in page.get("table") or []:
            if entry.get("name") == "Percentage Used Endurance Indicator":
                try:
                    return int(entry.get("value"))
                except (TypeError, ValueError):
                    return None
    return None


def _scsi_grown(payload: dict) -> int:
    try:
        return int(payload.get("scsi_grown_defect_list") or 0)
    except (TypeError, ValueError):
        return 0


def _scsi_uncorrected(payload: dict) -> int:
    log = payload.get("scsi_error_counter_log") or {}
    total = 0
    for key in ("read", "write", "verify"):
        section = log.get(key) or {}
        try:
            total += int(section.get("total_uncorrected_errors") or 0)
        except (TypeError, ValueError):
            continue
    return total


def _smart_failed(payload: dict) -> bool:
    status = payload.get("smart_status")
    if isinstance(status, dict):
        return status.get("passed") is False
    return False


def _selftest_grade(payload: dict, protocol: str, current_poh: int) -> str:
    """§10 self-test history: A / C / D / F from recent vs old failures."""
    failed_hours: list[int | None] = []

    if protocol == "ATA":
        table = ((payload.get("ata_smart_self_test_log") or {}).get("standard") or {}).get("table") or []
        for entry in table:
            status = (entry or {}).get("status") or {}
            if status.get("passed") is False:
                hours = entry.get("lifetime_hours")
                try:
                    failed_hours.append(int(hours) if hours is not None else None)
                except (TypeError, ValueError):
                    failed_hours.append(None)
    elif protocol == "SCSI":
        for key, value in payload.items():
            if not str(key).startswith("scsi_self_test_"):
                continue
            result = (value or {}).get("result") or {}
            text = str(result.get("string") or result).lower()
            if "fail" in text or "error" in text:
                pot = (value or {}).get("power_on_time") or {}
                hours = pot.get("hours", pot.get("aggregate"))
                try:
                    failed_hours.append(int(hours) if hours is not None else None)
                except (TypeError, ValueError):
                    failed_hours.append(None)
    elif protocol == "NVME":
        table = (payload.get("nvme_self_test_log") or {}).get("table") or []
        for entry in table:
            result = (entry or {}).get("self_test_result") or {}
            try:
                code = int(result.get("value", 0) or 0)
            except (TypeError, ValueError):
                code = 0
            if code == 1:
                hours = entry.get("power_on_hours")
                try:
                    failed_hours.append(int(hours) if hours is not None else None)
                except (TypeError, ValueError):
                    failed_hours.append(None)

    if not failed_hours:
        return "A"

    recent = 0
    old = 0
    for hours in failed_hours:
        if hours is None or (current_poh - hours) <= SELFTEST_RECENT_POH_WINDOW:
            recent += 1
        else:
            old += 1

    if recent >= 2:
        return "F"
    if recent == 1 or old >= 2:
        return "D"
    if old == 1:
        return "C"
    return "A"


def _age_cap_grade(poh: int, *, enterprise: bool) -> str:
    """§5 age cap."""
    if enterprise:
        if poh > 60000:
            return "C"
        if poh > 40000:
            return "B"
        return "A"
    if poh > 60000:
        return "D"
    if poh > 20000:
        return "B"
    return "A"


def _ssd_wear_grade(pct_used: int) -> str:
    """
    Reconstructed §7 / §9 wear grades used by Finding 8 fixtures.

    Mid-life (~55%) → B; end-of-life (>=90%) → F. Exact standard tables
    for ATA SSD wear were not independently verifiable from fleet data.
    """
    if pct_used >= 90:
        return "F"
    if pct_used >= 50:
        return "B"
    return "A"


def compute_standard_grade(payload: dict) -> tuple[str, str]:
    """
    Independently compute the Revert Standard final grade (Finding 8 method).

    Returns ``(final_grade, certification)``.
    """
    protocol = _protocol(payload)
    poh = _poh(payload)
    enterprise = protocol in ("SCSI", "NVME")

    # Stage 1 fail-gates
    if _smart_failed(payload):
        return "F", certification_for_grade("F")
    if protocol == "SCSI" and _scsi_grown(payload) > 100:
        return "F", certification_for_grade("F")
    if protocol == "ATA" and _ata_attr_raw(payload, 5) > 100:
        return "F", certification_for_grade("F")
    if protocol == "NVME":
        health = payload.get("nvme_smart_health_information_log") or {}
        try:
            cw = int(health.get("critical_warning") or 0)
        except (TypeError, ValueError):
            cw = 0
        try:
            media = int(health.get("media_errors") or 0)
        except (TypeError, ValueError):
            media = 0
        spare = health.get("available_spare")
        spare_thr = health.get("available_spare_threshold", 10)
        try:
            spare_i = int(spare) if spare is not None else None
            thr_i = int(spare_thr) if spare_thr is not None else 10
        except (TypeError, ValueError):
            spare_i, thr_i = None, 10
        if cw != 0 or media > 0 or (spare_i is not None and spare_i < thr_i):
            return "F", certification_for_grade("F")

    attribute_grades: list[str] = []

    if protocol == "ATA":
        # Sector-count attributes (§6): 5 / 197 / 198
        for attr_id in (5, 197, 198):
            attribute_grades.append(band_grade(_ata_attr_raw(payload, attr_id), DEFECT_BANDS))
        # Error-count attributes (§6): 187 / 188 / 199
        for attr_id in (187, 188, 199):
            attribute_grades.append(band_grade(_ata_attr_raw(payload, attr_id), ERROR_BANDS))
        if _is_ssd(payload):
            pct = _ssd_pct_used(payload)
            if pct is not None:
                attribute_grades.append(_ssd_wear_grade(pct))
    elif protocol == "SCSI":
        attribute_grades.append(band_grade(_scsi_grown(payload), DEFECT_BANDS))
        attribute_grades.append(band_grade(_scsi_uncorrected(payload), ERROR_BANDS))
    elif protocol == "NVME":
        pct = _ssd_pct_used(payload)
        if pct is not None:
            attribute_grades.append(_ssd_wear_grade(pct))

    attribute_grades.append(_selftest_grade(payload, protocol, poh))

    defect = "A"
    for g in attribute_grades:
        defect = worst_grade(defect, g)

    # §12.5 multi-factor: 3+ attributes independently C-or-worse → escalate one level
    c_or_worse = sum(1 for g in attribute_grades if _GRADE_RANK[g] >= _GRADE_RANK["C"])
    if c_or_worse >= 3 and defect != "F":
        defect = GRADE_ORDER[_GRADE_RANK[defect] + 1]

    age_cap = _age_cap_grade(poh, enterprise=enterprise)
    final = worst_grade(defect, age_cap)
    return final, certification_for_grade(final)


# Hardcoded expected grades (Finding 8 pins + section band fixtures).
# Kept as the regression oracle; ``compute_standard_grade`` must agree.
EXPECTED_GRADES: dict[str, str] = {
    # §6 ATA HDD defect bands
    "ata_hdd_defects_band_a": "A",
    "ata_hdd_defects_band_b": "B",
    "ata_hdd_defects_band_c": "C",
    "ata_hdd_defects_band_d": "D",
    "ata_hdd_defects_band_f": "F",
    # §7 ATA SSD wear (reconstructed; tool wear graduation pending)
    "ata_ssd_midlife_wear": "B",
    "ata_ssd_end_of_life_wear": "F",
    # §9 NVMe Log Page 02h
    "nvme_healthy_log_page_02h": "A",
    "nvme_critical_warning_high_wear": "F",
    # §5 age cap
    "sas_enterprise_45k_poh_clean": "B",
    "sas_enterprise_65k_poh_clean": "C",
    "ata_consumer_25k_poh_clean": "B",
    "ata_consumer_65k_poh_clean": "D",
    # §8 SCSI graduated bands
    "scsi_defects_clean": "A",
    "scsi_grown_defects_band_b": "B",
    "scsi_grown_defects_band_c": "C",
    "scsi_grown_defects_band_d": "D",
    "scsi_grown_defects_band_f": "F",
    "scsi_uncorrected_band_b": "B",
    "scsi_uncorrected_band_c": "C",
    "scsi_uncorrected_band_d": "D",
    "scsi_uncorrected_band_f": "F",
    # §10 self-test history
    "ata_selftest_one_old_failure": "C",
    "ata_selftest_two_old_failures": "D",
    "ata_selftest_one_recent_failure": "D",
    "ata_selftest_two_recent_failures": "F",
    "scsi_selftest_only_failure": "D",
    # Finding 8 report serials
    "report_1SHK383Z": "C",
    "report_JEHXTXVN": "C",
    "report_1SHKKWGZ": "C",
    "report_ZC19AACC": "C",
    "report_ZAD2AZ2A": "F",
    "report_ZAD2AX9T": "F",
}

FIXTURE_SECTIONS: dict[str, str] = {
    "ata_hdd_defects_band_a": "§6 ATA HDD defects",
    "ata_hdd_defects_band_b": "§6 ATA HDD defects",
    "ata_hdd_defects_band_c": "§6 ATA HDD defects",
    "ata_hdd_defects_band_d": "§6 ATA HDD defects",
    "ata_hdd_defects_band_f": "§6 ATA HDD defects",
    "ata_ssd_midlife_wear": "§7 ATA SSD wear",
    "ata_ssd_end_of_life_wear": "§7 ATA SSD wear",
    "nvme_healthy_log_page_02h": "§9 NVMe Log Page 02h",
    "nvme_critical_warning_high_wear": "§9 NVMe Log Page 02h",
    "sas_enterprise_45k_poh_clean": "§5 age cap",
    "sas_enterprise_65k_poh_clean": "§5 age cap",
    "ata_consumer_25k_poh_clean": "§5 age cap",
    "ata_consumer_65k_poh_clean": "§5 age cap",
    "scsi_defects_clean": "§8 SCSI defects",
    "scsi_grown_defects_band_b": "§8 SCSI grown defects",
    "scsi_grown_defects_band_c": "§8 SCSI grown defects",
    "scsi_grown_defects_band_d": "§8 SCSI grown defects",
    "scsi_grown_defects_band_f": "§8 SCSI grown defects",
    "scsi_uncorrected_band_b": "§8 SCSI uncorrected errors",
    "scsi_uncorrected_band_c": "§8 SCSI uncorrected errors",
    "scsi_uncorrected_band_d": "§8 SCSI uncorrected errors",
    "scsi_uncorrected_band_f": "§8 SCSI uncorrected errors",
    "ata_selftest_one_old_failure": "§10 self-test history",
    "ata_selftest_two_old_failures": "§10 self-test history",
    "ata_selftest_one_recent_failure": "§10 self-test history",
    "ata_selftest_two_recent_failures": "§10 self-test history",
    "scsi_selftest_only_failure": "§10 self-test history",
    "report_1SHK383Z": "Finding 8 report serials",
    "report_JEHXTXVN": "Finding 8 report serials",
    "report_1SHKKWGZ": "Finding 8 report serials",
    "report_ZC19AACC": "Finding 8 report serials",
    "report_ZAD2AZ2A": "Finding 8 report serials",
    "report_ZAD2AX9T": "Finding 8 report serials",
}
