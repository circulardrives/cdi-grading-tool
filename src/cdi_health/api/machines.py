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

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal

DEFAULT_DATA_DIR_ENV = "CDI_HEALTH_DATA_DIR"

MachineStatus = Literal["unknown", "reachable", "unreachable"]
ScanStatus = Literal["success", "failed"]


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def resolve_data_dir() -> Path:
    """Resolve the persistent data directory for API state."""
    configured = os.getenv(DEFAULT_DATA_DIR_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / ".cdi-health").resolve()


class MachineStore:
    """JSON-backed registry of grading hosts and their latest scan snapshots."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = (data_dir or resolve_data_dir()).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.data_dir / "machines.json"
        self.lock = Lock()
        self._machines: dict[str, dict[str, Any]] = {}
        self._latest_scans: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.store_path.is_file():
            return

        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        machines = payload.get("machines", [])
        if isinstance(machines, list):
            for entry in machines:
                if isinstance(entry, dict) and entry.get("id"):
                    self._machines[str(entry["id"])] = entry

        scans = payload.get("latest_scans", {})
        if isinstance(scans, dict):
            self._latest_scans = {str(key): value for key, value in scans.items() if isinstance(value, dict)}

    def _save(self) -> None:
        payload = {
            "machines": sorted(
                self._machines.values(),
                key=lambda item: item.get("created_at", ""),
            ),
            "latest_scans": self._latest_scans,
        }
        temp_path = self.store_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_path.replace(self.store_path)

    def list_machines(self) -> list[dict[str, Any]]:
        with self.lock:
            return [
                dict(entry)
                for entry in sorted(
                    self._machines.values(),
                    key=lambda item: item.get("name", "").lower(),
                )
            ]

    def get_machine(self, machine_id: str) -> dict[str, Any] | None:
        with self.lock:
            entry = self._machines.get(machine_id)
            return dict(entry) if entry else None

    def create_machine(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now_iso()
        entry = {
            "id": str(uuid.uuid4()),
            "name": payload["name"].strip(),
            "hostname": payload["hostname"].strip(),
            "address": payload.get("address", "").strip(),
            "location": payload.get("location", "").strip(),
            "notes": payload.get("notes", "").strip(),
            "status": "unknown",
            "last_seen_at": None,
            "last_scan_at": None,
            "last_scan_status": None,
            "last_scan_summary": None,
            "created_at": now,
            "updated_at": now,
        }
        with self.lock:
            self._machines[entry["id"]] = entry
            self._save()
        return dict(entry)

    def update_machine(self, machine_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        with self.lock:
            entry = self._machines.get(machine_id)
            if not entry:
                return None

            for field in ("name", "hostname", "address", "location", "notes", "status"):
                if field in payload and payload[field] is not None:
                    value = payload[field]
                    entry[field] = value.strip() if isinstance(value, str) else value

            entry["updated_at"] = utc_now_iso()
            self._machines[machine_id] = entry
            self._save()
            return dict(entry)

    def delete_machine(self, machine_id: str) -> bool:
        with self.lock:
            if machine_id not in self._machines:
                return False
            del self._machines[machine_id]
            self._latest_scans.pop(machine_id, None)
            self._save()
            return True

    def record_scan(
        self,
        machine_id: str,
        scan_result: dict[str, Any],
        *,
        success: bool = True,
    ) -> dict[str, Any] | None:
        summary = scan_result.get("summary") or {}
        now = utc_now_iso()
        with self.lock:
            entry = self._machines.get(machine_id)
            if not entry:
                return None

            entry["last_scan_at"] = scan_result.get("scanned_at") or now
            entry["last_scan_status"] = "success" if success else "failed"
            entry["last_scan_summary"] = {
                "total": int(summary.get("total", 0)),
                "healthy": int(summary.get("healthy", 0)),
                "warning": int(summary.get("warning", 0)),
                "failed": int(summary.get("failed", 0)),
            }
            entry["last_seen_at"] = now
            entry["status"] = "reachable" if success else entry.get("status", "unknown")
            entry["updated_at"] = now
            self._machines[machine_id] = entry
            self._latest_scans[machine_id] = dict(scan_result)
            self._save()
            return dict(entry)

    def get_scan(self, machine_id: str) -> dict[str, Any] | None:
        with self.lock:
            scan = self._latest_scans.get(machine_id)
            return dict(scan) if scan else None
