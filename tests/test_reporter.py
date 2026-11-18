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

"""Tests for HTML/CSV report generation."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from cdi_health.classes.mock import MockDevices, create_mock_device
from cdi_health.classes.reporter import ReportGenerator


def _mock_device(mock_data_dir: Path, relative: str) -> dict:
    """One parsed device record from a mock smartctl capture."""
    return create_mock_device(json_file=str(mock_data_dir / relative)).to_dict(pop=True)


def _evidence_cards(html_text: str) -> dict[str, str]:
    """Evidence card HTML by its title (the drive's serial label)."""
    cards = {}
    for card in re.findall(r'<article class="evidence-card">.*?</article>', html_text, flags=re.DOTALL):
        title = re.search(r'<h3 class="evidence-card__title">(.*?)</h3>', card, flags=re.DOTALL)
        cards[title.group(1).strip() if title else ""] = card
    return cards


def test_html_evidence_card_lists_the_drives_deductions(tmp_path: Path, mock_data_dir: Path) -> None:
    """A failed drive's card must say why (regression: every card read "No score deductions")."""
    failed = _mock_device(mock_data_dir, "scsi/high_grown_defects.json")
    healthy = _mock_device(mock_data_dir, "scsi/healthy_sas.json")

    out = tmp_path / "report.html"
    ReportGenerator().generate_html([failed, healthy], str(out))
    cards = _evidence_cards(out.read_text(encoding="utf-8"))

    failed_card = next(card for title, card in cards.items() if failed["serial_number"] in title)
    assert 'class="deduction-list"' in failed_card
    assert "Grown defects" in failed_card
    assert "No score deductions" not in failed_card

    healthy_card = next(card for title, card in cards.items() if healthy["serial_number"] in title)
    assert "No score deductions" in healthy_card


def test_csv_report_deductions_column_is_filled(tmp_path: Path, mock_data_dir: Path) -> None:
    failed = _mock_device(mock_data_dir, "scsi/high_grown_defects.json")
    healthy = _mock_device(mock_data_dir, "scsi/healthy_sas.json")

    out = tmp_path / "report.csv"
    ReportGenerator().generate_csv([failed, healthy], str(out))
    with out.open(encoding="utf-8-sig", newline="") as handle:
        rows = {row["Serial"]: row for row in csv.DictReader(handle)}

    assert "Grown defects" in rows[failed["serial_number"]]["Deductions"]
    assert rows[healthy["serial_number"]]["Deductions"] == "—"


def test_report_from_saved_scan_keeps_recorded_deductions(tmp_path: Path) -> None:
    """Saved API scans store deductions as dicts under ``deductions``."""
    recorded = {
        "dut": "/dev/sdb",
        "serial_number": "SAVED-1",
        "model_number": "SAVED MODEL",
        "transport_protocol": "SCSI",
        "media_type": "HDD",
        "health_grade": "C",
        "health_score": 70,
        "health_status": "Fair",
        "is_certified": True,
        "deductions": [
            {
                "reason": "Grown defects",
                "points": 30,
                "severity": "warning",
                "field": "grown_defects",
                "value": 31,
                "threshold": 100,
                "attribute_grade": "C",
            }
        ],
    }
    out = tmp_path / "saved.html"
    ReportGenerator(preserve_grades=True).generate_html([recorded], str(out))
    card = next(iter(_evidence_cards(out.read_text(encoding="utf-8")).values()))
    assert "Grown defects" in card
    assert "(grade C)" in card


def test_ungraded_card_does_not_claim_metrics_within_policy(tmp_path: Path, mock_data_dir: Path) -> None:
    """Nothing was evaluated on an unreadable drive, so "within policy" would be false."""
    unreadable = _mock_device(mock_data_dir, "nvme/bad_drive_SKHynix_PE6110_unavailable.json")
    out = tmp_path / "ungraded.html"
    ReportGenerator().generate_html([unreadable], str(out))
    card = next(iter(_evidence_cards(out.read_text(encoding="utf-8")).values()))
    assert "Not graded" in card
    assert "metrics within policy" not in card


def test_generate_csv_includes_nvme_columns_and_category(tmp_path: Path, mock_data_dir: Path) -> None:
    """CSV export unions advanced columns; NVMe drives get scalar log fields + full JSON columns."""
    devices = MockDevices(
        mock_data_path=str(mock_data_dir),
        ignore_ata=False,
        ignore_nvme=False,
        ignore_scsi=False,
    ).devices
    assert len(devices) > 0

    out = tmp_path / "fleet.csv"
    ReportGenerator().generate_csv(devices, str(out))

    text = out.read_text(encoding="utf-8-sig")
    assert "Report category" in text
    assert "NVMe data units read" in text
    assert "NVMe error log —" in text
    assert "NVMe error log (full JSON)" in text
    assert "NVMe self-test log (full JSON)" in text
    assert "OCP SMART C0h (full JSON)" in text
    assert "SMART attr" in text


def test_generate_html_includes_nvme_modal_and_log_buttons(tmp_path: Path, mock_data_dir: Path) -> None:
    """HTML report embeds JSON modal and per-row log buttons for NVMe (no giant table cells)."""
    devices = MockDevices(
        mock_data_path=str(mock_data_dir),
        ignore_ata=False,
        ignore_nvme=False,
        ignore_scsi=False,
    ).devices
    assert any(d.get("transport_protocol") == "NVMe" for d in devices)

    out = tmp_path / "report.html"
    ReportGenerator().generate_html(devices, str(out))
    html_text = out.read_text(encoding="utf-8")

    assert 'id="cdi-json-modal"' in html_text
    assert "btn-json-log" in html_text
    assert "cdiJsonModal" in html_text
    assert "nvme-json-blobs" in html_text
    assert "OCP C0h" in html_text


def test_generate_html_shadcn_style_evidence_cards(tmp_path: Path, mock_data_dir: Path) -> None:
    """Simple HTML view uses dashboard-aligned fonts, badges, and per-drive evidence cards."""
    devices = MockDevices(
        mock_data_path=str(mock_data_dir),
        ignore_ata=True,
        ignore_nvme=False,
        ignore_scsi=True,
    ).devices
    assert devices

    out = tmp_path / "report-shadcn.html"
    ReportGenerator().generate_html(devices, str(out))
    html_text = out.read_text(encoding="utf-8")

    assert "Source Sans 3" in html_text
    assert "JetBrains Mono" in html_text
    assert "--background" in html_text
    assert "evidence-card" in html_text
    assert "evidence-grid" in html_text
    assert "Certification rationale" in html_text
    assert "badge--" in html_text
    assert "device-table--simple" in html_text


def test_nvme_scalar_keys_skip_nested_log_fields() -> None:
    """Union of NVMe error log keys excludes list/dict values (those go to JSON viewers)."""
    devices = [
        {
            "transport_protocol": "NVMe",
            "nvme_error_information_log": {"size": 256, "read": 1, "table": [{"a": 1}]},
        }
    ]
    keys = ReportGenerator._nvme_scalar_keys_union(devices, "nvme_error_information_log")
    assert "size" in keys
    assert "read" in keys
    assert "table" not in keys


def test_nvme_scalar_keys_skip_blob_keys_case_insensitive() -> None:
    """Array-like log keys are skipped regardless of smartctl key casing."""
    devices = [
        {
            "transport_protocol": "NVMe",
            "nvme_self_test_log": {
                "TABLE": [{"x": 1}],
                "current_self_test_operation": {"value": 0, "string": "Idle"},
            },
        }
    ]
    keys = ReportGenerator._nvme_scalar_keys_union(devices, "nvme_self_test_log")
    assert "TABLE" not in keys
    assert "current_self_test_operation" not in keys


def test_nvme_selftest_scalar_field_rejects_jsonish_strings() -> None:
    """Long JSON-looking strings must not blow up table cells."""
    blob = '[{"self_test_code": {"value": 1}}]'
    device = {
        "transport_protocol": "NVMe",
        "nvme_self_test_log": {"weird": blob * 50},
    }
    cell = ReportGenerator._nvme_selftest_scalar_field(device, "weird")
    assert cell == "—"


def test_format_ocp_smart_value_hi_lo() -> None:
    assert ReportGenerator._format_ocp_smart_value({"hi": 0, "lo": 42}) == "42"
    assert ReportGenerator._format_ocp_smart_value({"hi": 1, "lo": 0}) == str(1 << 64)


def test_normalize_display_value_smartctl_dict() -> None:
    text, variant = ReportGenerator._normalize_display_value({"name": "SAS (SPL-4)", "value": 6})
    assert text == "SAS (SPL-4)"
    assert variant == ""


def test_generate_html_advanced_table_uses_inner_clamp_spans(tmp_path: Path, mock_data_dir: Path) -> None:
    """Advanced cells must not apply line-clamp display on <td> (breaks column layout)."""
    devices = MockDevices(
        mock_data_path=str(mock_data_dir),
        ignore_ata=False,
        ignore_nvme=False,
        ignore_scsi=False,
    ).devices
    out = tmp_path / "report.html"
    ReportGenerator().generate_html(devices, str(out))
    html_text = out.read_text(encoding="utf-8")
    assert "cell-stat__clamp" in html_text
    assert "cell-stat:not(.cell-stat--is-multiline)" not in html_text
    assert '<td class="cell-stat"><span class="cell-stat__clamp">' in html_text


def test_generate_html_includes_ocp_columns_when_present(tmp_path: Path, mock_data_dir: Path) -> None:
    """NVMe devices with OCP C0h data get per-field columns with readable hi/lo counters."""
    devices = MockDevices(
        mock_data_path=str(mock_data_dir),
        ignore_ata=True,
        ignore_nvme=False,
        ignore_scsi=True,
    ).devices
    with_ocp = [d for d in devices if isinstance(d.get("ocp_smart_log"), dict) and d["ocp_smart_log"]]
    if not with_ocp:
        return

    out = tmp_path / "report.html"
    ReportGenerator().generate_html(devices, str(out))
    html_text = out.read_text(encoding="utf-8")
    assert "OCP SMART — Bad user nand blocks - Normalized" in html_text
    # FADU fixture: Physical media units read {hi:0, lo:2744719892480} → single 128-bit style integer string
    assert "2744719892480" in html_text


def test_format_deductions_short_prefers_attribute_grade_over_points() -> None:
    """#119: graduated bands display [grade X], not cosmetic [-N]."""
    from cdi_health.classes.scoring import ScoreDeduction

    banded = ScoreDeduction(
        reason="Grown defects",
        points=25,
        severity="warning",
        field="grown_defects",
        value=25,
        threshold=100,
        attribute_grade="C",
    )
    warning = ScoreDeduction(
        reason="Temperature warning",
        points=5,
        severity="warning",
        field="temperature",
        value=55,
        threshold=50,
    )
    rg = ReportGenerator()
    short = rg._format_deductions_short([banded, warning])
    assert "[grade C]" in short
    assert "[-25]" not in short
    assert "[-5]" in short

    html = rg._render_deduction_list([banded, warning])
    assert "(grade C)" in html
    assert "(−25)" not in html
    assert "(−5)" in html
