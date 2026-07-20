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

"""Persisted scan history under the API data directory (one JSON file per scan)."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

from cdi_health.api.machines import resolve_data_dir, utc_now_iso

HISTORY_ID_PATTERN = re.compile(
    r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{8}$",
    re.IGNORECASE,
)


def _safe_history_id(scan_id: str) -> str | None:
    """Return a validated history id, or None if unsafe/invalid."""
    if not scan_id or "/" in scan_id or "\\" in scan_id or ".." in scan_id:
        return None
    if not HISTORY_ID_PATTERN.fullmatch(scan_id):
        return None
    return scan_id


def _grade_counts(devices: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for device in devices:
        grade = str(device.get("health_grade") or "?").upper()
        counts[grade] = counts.get(grade, 0) + 1
    return dict(sorted(counts.items()))


class ScanHistoryStore:
    """Append-only scan history as one JSON snapshot file per successful scan."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = (data_dir or resolve_data_dir()).resolve()
        self.history_dir = self.data_dir / "scan-history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()

    def _path_for(self, scan_id: str) -> Path | None:
        safe = _safe_history_id(scan_id)
        if not safe:
            return None
        path = (self.history_dir / f"{safe}.json").resolve()
        try:
            path.relative_to(self.history_dir.resolve())
        except ValueError:
            return None
        return path

    def record_scan(
        self,
        scan_result: dict[str, Any],
        *,
        machine_id: str | None = None,
        mock: bool = False,
    ) -> dict[str, Any]:
        """Persist a successful scan snapshot and return the history entry."""
        summary = scan_result.get("summary") or {}
        devices = scan_result.get("devices") or []
        if not isinstance(devices, list):
            devices = []

        scanned_at = str(scan_result.get("scanned_at") or utc_now_iso())
        # Prefer a sortable filename prefix from the scan timestamp.
        stamp = scanned_at.replace("-", "").replace(":", "").replace("T", "-")[:15]
        if len(stamp) < 15:
            stamp = utc_now_iso().replace("-", "").replace(":", "").replace("T", "-")[:15]
        scan_id = f"{stamp}-{uuid.uuid4().hex[:8]}"

        entry = {
            "id": scan_id,
            "scanned_at": scanned_at,
            "created_at": utc_now_iso(),
            "machine_id": machine_id,
            "mock": bool(mock),
            "device_count": len(devices),
            "summary": {
                "total": int(summary.get("total", len(devices))),
                "healthy": int(summary.get("healthy", 0)),
                "warning": int(summary.get("warning", 0)),
                "failed": int(summary.get("failed", 0)),
            },
            "grades": _grade_counts(devices),
            "devices": devices,
        }

        path = self._path_for(scan_id)
        if path is None:
            raise ValueError(f"Invalid history id generated: {scan_id}")

        with self.lock:
            temp_path = path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
            temp_path.replace(path)
        return entry

    def list_scans(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        machine_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return newest-first scan summaries (without device payloads)."""
        entries: list[dict[str, Any]] = []
        with self.lock:
            files = sorted(self.history_dir.glob("*.json"), reverse=True)
            for path in files:
                if path.name.endswith(".tmp"):
                    continue
                scan_id = path.stem
                if not _safe_history_id(scan_id):
                    continue
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                if machine_id is not None and payload.get("machine_id") != machine_id:
                    continue
                entries.append(self._to_summary(payload, fallback_id=scan_id))

        return entries[offset : offset + limit]

    def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """Load a full scan snapshot by id."""
        path = self._path_for(scan_id)
        if path is None or not path.is_file():
            return None
        with self.lock:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
        if not isinstance(payload, dict):
            return None
        payload.setdefault("id", scan_id)
        devices = payload.get("devices")
        if not isinstance(devices, list):
            payload["devices"] = []
        summary = payload.get("summary") or {}
        payload["summary"] = {
            "total": int(summary.get("total", len(payload["devices"]))),
            "healthy": int(summary.get("healthy", 0)),
            "warning": int(summary.get("warning", 0)),
            "failed": int(summary.get("failed", 0)),
        }
        payload.setdefault("device_count", len(payload["devices"]))
        payload.setdefault("grades", _grade_counts(payload["devices"]))
        payload.setdefault("mock", False)
        payload.setdefault("machine_id", None)
        payload.setdefault("created_at", payload.get("scanned_at"))
        return payload

    def delete_scan(self, scan_id: str) -> bool:
        """Delete one history snapshot. Returns True if a file was removed."""
        path = self._path_for(scan_id)
        if path is None or not path.is_file():
            return False
        with self.lock:
            try:
                path.unlink()
            except OSError:
                return False
        return True

    def clear_scans(self) -> int:
        """Delete all history snapshots. Returns the number of files removed."""
        deleted = 0
        with self.lock:
            for path in self.history_dir.glob("*.json"):
                if path.name.endswith(".tmp"):
                    continue
                if not _safe_history_id(path.stem):
                    continue
                try:
                    path.unlink()
                    deleted += 1
                except OSError:
                    continue
            # Drop leftover temp writes from interrupted records.
            for path in self.history_dir.glob("*.tmp"):
                try:
                    path.unlink()
                except OSError:
                    continue
        return deleted

    @staticmethod
    def _to_summary(payload: dict[str, Any], *, fallback_id: str) -> dict[str, Any]:
        devices = payload.get("devices") if isinstance(payload.get("devices"), list) else []
        summary = payload.get("summary") or {}
        grades = payload.get("grades")
        if not isinstance(grades, dict):
            grades = _grade_counts(devices)
        return {
            "id": str(payload.get("id") or fallback_id),
            "scanned_at": payload.get("scanned_at"),
            "created_at": payload.get("created_at") or payload.get("scanned_at"),
            "machine_id": payload.get("machine_id"),
            "mock": bool(payload.get("mock", False)),
            "device_count": int(payload.get("device_count", len(devices))),
            "summary": {
                "total": int(summary.get("total", len(devices))),
                "healthy": int(summary.get("healthy", 0)),
                "warning": int(summary.get("warning", 0)),
                "failed": int(summary.get("failed", 0)),
            },
            "grades": {str(k): int(v) for k, v in grades.items()},
        }
