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
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal

DEFAULT_DATA_DIR_ENV = "CDI_HEALTH_DATA_DIR"

MachineStatus = Literal["unknown", "reachable", "unreachable", "auth_failed"]
MACHINE_STATUSES = ("unknown", "reachable", "unreachable", "auth_failed")
# Write-only secret: persisted in machines.json, never returned by the API.
TOKEN_FIELD = "api_token"
STORE_FILE_MODE = 0o600
ScanStatus = Literal["success", "failed"]
# Random per-install id (uuid4 hex) reported in /health so a dashboard can
# recognise itself among discovered or registered benches.
INSTANCE_ID_FILE = "instance_id"
_INSTANCE_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def resolve_data_dir() -> Path:
    """Resolve the persistent data directory for API state."""
    configured = os.getenv(DEFAULT_DATA_DIR_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / ".cdi-health").resolve()


def load_or_create_instance_id(data_dir: Path) -> str:
    """Return this install's persistent instance id, creating it once (mode 0600).

    If the data directory is not writable the id still works for the life of
    the process; it just changes on the next restart.
    """
    path = data_dir / INSTANCE_ID_FILE
    try:
        existing = path.read_text(encoding="utf-8").strip()
    except OSError:
        existing = ""
    if _INSTANCE_ID_RE.match(existing):
        return existing

    instance_id = uuid.uuid4().hex
    temp_path = path.with_suffix(".tmp")
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, STORE_FILE_MODE)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(instance_id + "\n")
        os.chmod(temp_path, STORE_FILE_MODE)
        temp_path.replace(path)
    except OSError:
        pass
    return instance_id


def _normalize_token(value: Any) -> str | None:
    """Return a stripped token, or None when empty (empty string clears it)."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def public_machine(entry: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a machine record that is safe to expose (no token)."""
    public = {key: value for key, value in entry.items() if key != TOKEN_FIELD}
    public["has_api_token"] = bool(entry.get(TOKEN_FIELD))
    public.setdefault("remote_version", None)
    public.setdefault("remote_hostname", None)
    public.setdefault("remote_auth", None)
    public.setdefault("remote_instance_id", None)
    return public


class MachineStore:
    """JSON-backed registry of grading hosts and their latest scan snapshots.

    Remote host API tokens are stored in plaintext in ``machines.json`` (file
    mode 0600). Every public accessor strips the token and exposes only
    ``has_api_token``; use :meth:`get_api_token` to read it for forwarding.
    """

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

        # Tighten stores written by older versions (before tokens were stored).
        try:
            os.chmod(self.store_path, STORE_FILE_MODE)
        except OSError:
            pass

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
        # The store holds remote API tokens: create it owner-read/write only.
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, STORE_FILE_MODE)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2))
        # O_CREAT's mode is ignored for a pre-existing temp file; enforce it.
        os.chmod(temp_path, STORE_FILE_MODE)
        temp_path.replace(self.store_path)

    def list_machines(self) -> list[dict[str, Any]]:
        with self.lock:
            return [
                public_machine(entry)
                for entry in sorted(
                    self._machines.values(),
                    key=lambda item: item.get("name", "").lower(),
                )
            ]

    def get_machine(self, machine_id: str) -> dict[str, Any] | None:
        with self.lock:
            entry = self._machines.get(machine_id)
            return public_machine(entry) if entry else None

    def get_api_token(self, machine_id: str) -> str | None:
        """Return the stored remote API token for a machine (internal use only)."""
        with self.lock:
            entry = self._machines.get(machine_id)
            if not entry:
                return None
            return _normalize_token(entry.get(TOKEN_FIELD))

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
            "remote_version": None,
            "remote_hostname": None,
            "remote_auth": None,
            "last_seen_at": None,
            "last_scan_at": None,
            "last_scan_status": None,
            "last_scan_summary": None,
            "created_at": now,
            "updated_at": now,
        }
        token = _normalize_token(payload.get(TOKEN_FIELD))
        if token:
            entry[TOKEN_FIELD] = token
        with self.lock:
            self._machines[entry["id"]] = entry
            self._save()
        return public_machine(entry)

    def update_machine(self, machine_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        with self.lock:
            entry = self._machines.get(machine_id)
            if not entry:
                return None

            old_address = entry.get("address")
            for field in ("name", "hostname", "address", "location", "notes", "status"):
                if field in payload and payload[field] is not None:
                    value = payload[field]
                    entry[field] = value.strip() if isinstance(value, str) else value
            if entry.get("address") != old_address:
                # A new address may be a different bench; re-learn it on the next check.
                entry.pop("remote_instance_id", None)

            # Omitted (or null) = unchanged; "" clears; any other string replaces.
            if payload.get(TOKEN_FIELD) is not None:
                token = _normalize_token(payload[TOKEN_FIELD])
                if token:
                    entry[TOKEN_FIELD] = token
                else:
                    entry.pop(TOKEN_FIELD, None)

            entry["updated_at"] = utc_now_iso()
            self._machines[machine_id] = entry
            self._save()
            return public_machine(entry)

    def set_status(
        self,
        machine_id: str,
        status: str,
        *,
        seen: bool = False,
        remote_version: str | None = None,
        remote_auth: str | None = None,
        remote_hostname: str | None = None,
        remote_instance_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Update reachability status (and optionally last_seen/remote_version/remote_auth/remote_hostname/remote_instance_id)."""
        if status not in MACHINE_STATUSES:
            raise ValueError(f"Invalid machine status: {status}")
        now = utc_now_iso()
        with self.lock:
            entry = self._machines.get(machine_id)
            if not entry:
                return None
            entry["status"] = status
            if seen:
                entry["last_seen_at"] = now
            if remote_version is not None:
                entry["remote_version"] = remote_version
            if remote_auth in ("none", "token"):
                entry["remote_auth"] = remote_auth
            if remote_hostname:
                entry["remote_hostname"] = remote_hostname
            if remote_instance_id:
                entry["remote_instance_id"] = remote_instance_id
            entry["updated_at"] = now
            self._save()
            return public_machine(entry)

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
                "ungraded": int(summary.get("ungraded", 0)),
            }
            entry["last_seen_at"] = now
            entry["status"] = "reachable" if success else entry.get("status", "unknown")
            entry["updated_at"] = now
            self._machines[machine_id] = entry
            self._latest_scans[machine_id] = dict(scan_result)
            self._save()
            return public_machine(entry)

    def get_scan(self, machine_id: str) -> dict[str, Any] | None:
        with self.lock:
            scan = self._latest_scans.get(machine_id)
            return dict(scan) if scan else None
