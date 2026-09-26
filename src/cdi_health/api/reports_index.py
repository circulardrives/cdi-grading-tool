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

"""Persisted index of generated reports (``<data dir>/reports/index.json``).

The index lets ``GET /api/v1/reports`` list reports and ``GET
/api/v1/reports/{filename}`` serve them after an API restart. Only the newest
:data:`REPORT_INDEX_MAX_ENTRIES` records are kept; dropping a record never
deletes the report file itself.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

from cdi_health.api.machines import STORE_FILE_MODE, resolve_data_dir

REPORT_INDEX_MAX_ENTRIES = 200
INDEX_FILENAME = "index.json"
_RECORD_FIELDS = ("filename", "format", "generated_at", "source", "devices_count", "hosts", "output_file")


class ReportIndexStore:
    """JSON-backed list of generated reports, newest first."""

    def __init__(self, data_dir: Path | None = None, *, max_entries: int = REPORT_INDEX_MAX_ENTRIES) -> None:
        self.reports_dir = ((data_dir or resolve_data_dir()) / "reports").resolve()
        self.index_path = self.reports_dir / INDEX_FILENAME
        self.max_entries = max_entries
        self.lock = Lock()

    def _load(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        records = payload.get("reports") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            return []
        return [r for r in records if isinstance(r, dict) and isinstance(r.get("filename"), str)]

    def _save(self, records: list[dict[str, Any]]) -> None:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self.index_path.with_suffix(".tmp")
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, STORE_FILE_MODE)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"reports": records}, indent=2))
        os.chmod(temp_path, STORE_FILE_MODE)
        temp_path.replace(self.index_path)

    def add(self, result: dict[str, Any]) -> dict[str, Any]:
        """Record a generated report (replacing an older record for the same file)."""
        record = {key: result.get(key) for key in _RECORD_FIELDS}
        record["hosts"] = list(record.get("hosts") or [])
        record["source"] = record.get("source") or "scan"
        with self.lock:
            records = [r for r in self._load() if r.get("filename") != record["filename"]]
            records.insert(0, record)
            self._save(records[: self.max_entries])
        return record

    def list(self) -> list[dict[str, Any]]:
        """Newest-first records whose report file still exists."""
        with self.lock:
            records = self._load()
        records.sort(key=lambda r: str(r.get("generated_at") or ""), reverse=True)
        return [r for r in records if self._file_exists(r)]

    def paths(self) -> set[str]:
        """On-disk paths of indexed reports (for download resolution)."""
        with self.lock:
            records = self._load()
        return {str(r["output_file"]) for r in records if isinstance(r.get("output_file"), str)}

    def _file_exists(self, record: dict[str, Any]) -> bool:
        path = record.get("output_file")
        candidate = Path(path) if isinstance(path, str) and path else self.reports_dir / record["filename"]
        try:
            return candidate.is_file()
        except OSError:
            return False
