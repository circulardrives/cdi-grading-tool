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

"""Unit tests for ScanHistoryStore (JSON file persistence)."""

from __future__ import annotations

from pathlib import Path

from cdi_health.api.history import ScanHistoryStore


def _sample_scan(*, scanned_at: str = "2026-07-19T12:00:00+00:00") -> dict:
    return {
        "scanned_at": scanned_at,
        "summary": {"total": 2, "healthy": 1, "warning": 1, "failed": 0},
        "devices": [
            {"serial_number": "AAA", "health_grade": "A", "health_score": 95},
            {"serial_number": "BBB", "health_grade": "C", "health_score": 55},
        ],
    }


def test_record_and_list_scans(tmp_path: Path) -> None:
    store = ScanHistoryStore(data_dir=tmp_path)
    first = store.record_scan(_sample_scan(scanned_at="2026-07-19T10:00:00+00:00"), mock=True)
    second = store.record_scan(
        _sample_scan(scanned_at="2026-07-19T11:00:00+00:00"),
        machine_id="host-1",
        mock=False,
    )

    assert first["id"]
    assert (tmp_path / "scan-history" / f"{first['id']}.json").is_file()
    assert first["grades"] == {"A": 1, "C": 1}
    assert first["mock"] is True
    assert second["machine_id"] == "host-1"

    listed = store.list_scans()
    assert len(listed) == 2
    # Newest first by filename timestamp prefix.
    assert listed[0]["id"] == second["id"]
    assert "devices" not in listed[0]

    filtered = store.list_scans(machine_id="host-1")
    assert len(filtered) == 1
    assert filtered[0]["id"] == second["id"]


def test_get_scan_round_trip(tmp_path: Path) -> None:
    store = ScanHistoryStore(data_dir=tmp_path)
    saved = store.record_scan(_sample_scan())
    loaded = store.get_scan(saved["id"])
    assert loaded is not None
    assert loaded["id"] == saved["id"]
    assert len(loaded["devices"]) == 2
    assert loaded["summary"]["total"] == 2


def test_get_scan_rejects_path_traversal(tmp_path: Path) -> None:
    store = ScanHistoryStore(data_dir=tmp_path)
    assert store.get_scan("../etc/passwd") is None
    assert store.get_scan("not-a-valid-id") is None


def test_delete_scan(tmp_path: Path) -> None:
    store = ScanHistoryStore(data_dir=tmp_path)
    saved = store.record_scan(_sample_scan())
    assert store.delete_scan(saved["id"]) is True
    assert store.get_scan(saved["id"]) is None
    assert store.delete_scan(saved["id"]) is False
    assert store.delete_scan("../etc/passwd") is False


def test_clear_scans(tmp_path: Path) -> None:
    store = ScanHistoryStore(data_dir=tmp_path)
    store.record_scan(_sample_scan(scanned_at="2026-07-19T10:00:00+00:00"))
    store.record_scan(_sample_scan(scanned_at="2026-07-19T11:00:00+00:00"))
    assert len(store.list_scans()) == 2
    assert store.clear_scans() == 2
    assert store.list_scans() == []
    assert store.clear_scans() == 0
