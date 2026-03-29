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

from pathlib import Path

from cdi_health.classes.mock import MockDevices
from cdi_health.classes.reporter import ReportGenerator


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
