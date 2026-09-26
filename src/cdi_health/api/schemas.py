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

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# Strict NVMe controller/namespace paths only (no whitespace or extra tokens).
NVME_DEVICE_PATTERN = re.compile(r"^/dev/nvme[0-9]+(n[0-9]+)?$")
# Block-device style paths for scan/report filters (no shell metacharacters).
BLOCK_DEVICE_PATTERN = re.compile(r"^/dev/[a-zA-Z0-9][a-zA-Z0-9._+/-]*$")

GradingProfile = Literal["binary", "abcdf"]
MachineStatusValue = Literal["unknown", "reachable", "unreachable", "auth_failed"]
ExecutedOn = Literal["local", "remote"]
ReportSource = Literal["scan", "history", "fleet"]
ReportFormat = Literal["html", "pdf", "csv"]
# Max scan-history entries one "history" report may combine.
REPORT_MAX_HISTORY_IDS = 50


def _reject_path_traversal(value: str, field_name: str) -> str:
    if not value or "\x00" in value:
        raise ValueError(f"Invalid {field_name}")
    if any(part == ".." for part in Path(value).parts):
        raise ValueError(f"Invalid {field_name}: path traversal is not allowed")
    return value


def _validate_optional_fs_path(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _reject_path_traversal(value, field_name)


def _validate_optional_block_device(value: str | None) -> str | None:
    if value is None:
        return None
    if not BLOCK_DEVICE_PATTERN.fullmatch(value):
        raise ValueError("device must be a /dev path without whitespace or shell metacharacters")
    return value


def _validate_optional_nvme_device(value: str | None) -> str | None:
    if value is None:
        return None
    if not NVME_DEVICE_PATTERN.fullmatch(value):
        raise ValueError("device must match /dev/nvmeN or /dev/nvmeNnN")
    return value


def _validate_required_nvme_device(value: str) -> str:
    if not NVME_DEVICE_PATTERN.fullmatch(value):
        raise ValueError("device must match /dev/nvmeN or /dev/nvmeNnN")
    return value


class ScanRequest(BaseModel):
    """Scan request payload."""

    ignore_ata: bool = False
    ignore_nvme: bool = False
    ignore_scsi: bool = False
    device: str | None = None
    config: str | None = None
    mock_data: str | None = None
    mock_file: str | None = None
    grading_profile: GradingProfile | None = Field(
        default=None,
        description="Grading profile override (like --grading-profile); defaults to the config's grading.profile.",
    )
    machine_id: str | None = Field(
        default=None,
        description="Optional host registry ID to associate this scan with.",
    )

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str | None) -> str | None:
        return _validate_optional_block_device(value)

    @field_validator("config", "mock_data", "mock_file")
    @classmethod
    def validate_paths(cls, value: str | None, info: ValidationInfo) -> str | None:
        return _validate_optional_fs_path(value, info.field_name)


class ScanSummary(BaseModel):
    total: int
    healthy: int
    warning: int
    failed: int
    ungraded: int = 0


class ScanResponse(BaseModel):
    scanned_at: datetime
    grading_profile: GradingProfile | None = None
    summary: ScanSummary
    devices: list[dict[str, Any]]
    machine_id: str | None = None
    executed_on: ExecutedOn = Field(
        default="local",
        description="Where the scan ran: this API process (local) or a registered remote host.",
    )
    remote_address: str | None = Field(
        default=None,
        description="Remote host address the scan was forwarded to (remote scans only).",
    )


class HistorySummary(BaseModel):
    """Lightweight scan-history list entry (no device payloads)."""

    id: str
    scanned_at: datetime
    created_at: datetime | None = None
    machine_id: str | None = None
    mock: bool = False
    device_count: int
    grading_profile: GradingProfile | None = None
    summary: ScanSummary
    grades: dict[str, int] = Field(default_factory=dict)


class HistoryDetail(BaseModel):
    """Full persisted scan snapshot."""

    id: str
    scanned_at: datetime
    created_at: datetime | None = None
    machine_id: str | None = None
    mock: bool = False
    device_count: int
    grading_profile: GradingProfile | None = None
    summary: ScanSummary
    grades: dict[str, int] = Field(default_factory=dict)
    devices: list[dict[str, Any]]


class ReportRequest(BaseModel):
    """Report generation request payload."""

    format: ReportFormat = "html"
    source: ReportSource = Field(
        default="scan",
        description=(
            "scan: fresh scan of this API's drives (default). fleet: latest stored scan of every "
            "host (same set as GET /api/v1/fleet/devices). history: the listed scan-history entries. "
            "fleet/history never rescan and render the recorded grades as-is."
        ),
    )
    history_ids: list[str] | None = Field(
        default=None,
        description=f"Scan-history ids for source=history (1-{REPORT_MAX_HISTORY_IDS}).",
    )
    output_file: str | None = None
    ignore_ata: bool = False
    ignore_nvme: bool = False
    ignore_scsi: bool = False
    device: str | None = None
    config: str | None = None
    mock_data: str | None = None
    mock_file: str | None = None
    grading_profile: GradingProfile | None = None

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str | None) -> str | None:
        return _validate_optional_block_device(value)

    @field_validator("config", "mock_data", "mock_file", "output_file")
    @classmethod
    def validate_paths(cls, value: str | None, info: ValidationInfo) -> str | None:
        return _validate_optional_fs_path(value, info.field_name)


class ReportHost(BaseModel):
    """One host whose scan contributed devices to a report."""

    name: str
    machine_id: str | None = None
    scanned_at: str | None = None
    device_count: int = 0


class ReportResponse(BaseModel):
    generated_at: datetime
    output_file: str
    filename: str
    format: ReportFormat
    devices_count: int
    source: ReportSource = "scan"
    hosts: list[ReportHost] = Field(default_factory=list)


class ReportListEntry(BaseModel):
    """GET /api/v1/reports entry (persisted report index)."""

    filename: str
    format: ReportFormat
    generated_at: datetime
    source: ReportSource = "scan"
    devices_count: int = 0
    hosts: list[ReportHost] = Field(default_factory=list)


class SelfTestStartRequest(BaseModel):
    """Start self-test job request payload."""

    # Reject unknown fields: a misspelled "devices" must not silently fall back
    # to running self-tests on every supported drive.
    model_config = ConfigDict(extra="forbid")

    device: str | None = Field(
        default=None,
        description="Single NVMe controller path, e.g. /dev/nvme0. If omitted, run on all supported devices.",
    )
    test_type: Literal["short", "extended"] = "short"
    wait: bool = False
    poll_interval_seconds: int = Field(default=30, ge=5, le=600)
    timeout_seconds: int = Field(default=14_400, ge=60, le=172_800)
    machine_id: str | None = Field(
        default=None,
        description="Registered host to run on. A host with an address is forwarded to its API.",
    )

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str | None) -> str | None:
        return _validate_optional_nvme_device(value)


class SelfTestAbortRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device: str
    machine_id: str | None = Field(
        default=None,
        description="Registered host to abort on. A host with an address is forwarded to its API.",
    )

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str) -> str:
        return _validate_required_nvme_device(value)


class HealthResponse(BaseModel):
    status: str
    version: str
    hostname: str | None = Field(default=None, description="The bench's own hostname (socket.gethostname()).")
    is_root: bool | None = None
    allow_non_root_mode: bool | None = None
    api_token_enabled: bool | None = None
    auth_mode: Literal["none", "token"] | None = None
    missing_required_tools: list[str] | None = None
    weasyprint_available: bool | None = None
    message: str | None = None


class JobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    machine_id: str | None = Field(
        default=None,
        description="Remote host the job runs on (forwarded self-tests only); pass it back when polling.",
    )


class MachineScanSummary(BaseModel):
    total: int
    healthy: int
    warning: int
    failed: int
    ungraded: int = 0


class MachineCreate(BaseModel):
    """Register a grading host in the fleet registry."""

    name: str = Field(min_length=1, description="Display name shown in the dashboard.")
    hostname: str = Field(min_length=1, description="Host identifier, e.g. grading-01.local")
    address: str = Field(
        default="",
        description=(
            "Optional IP, host:port, or http://host:port of the host's cdi-health-api "
            "(default port 8844). When set, scans for this machine run on that host."
        ),
    )
    location: str = Field(default="", description="Optional rack or data-center location label.")
    notes: str = ""
    api_token: str | None = Field(
        default=None,
        max_length=4096,
        description="Write-only X-API-Token of the remote host's API. Never returned; see has_api_token.",
    )


class MachineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    hostname: str | None = Field(default=None, min_length=1)
    address: str | None = None
    location: str | None = None
    notes: str | None = None
    status: MachineStatusValue | None = None
    api_token: str | None = Field(
        default=None,
        max_length=4096,
        description='Write-only remote API token. Omit to keep it, "" to clear it.',
    )


class MachineResponse(BaseModel):
    id: str
    name: str
    hostname: str
    address: str
    location: str
    notes: str
    status: MachineStatusValue
    has_api_token: bool = False
    remote_version: str | None = None
    remote_hostname: str | None = Field(
        default=None,
        description="Hostname the remote bench reported in its /health payload (set by /check).",
    )
    remote_auth: Literal["none", "token"] | None = Field(
        default=None,
        description="Remote host's auth mode from its /health auth_mode (set by /check).",
    )
    last_seen_at: datetime | None = None
    last_scan_at: datetime | None = None
    last_scan_status: Literal["success", "failed"] | None = None
    last_scan_summary: MachineScanSummary | None = None
    created_at: datetime
    updated_at: datetime


class MachineCheckResponse(BaseModel):
    """Result of POST /api/v1/machines/{id}/check."""

    machine: MachineResponse
    health: dict[str, Any] | None = None
    error: str | None = None


class FleetHost(BaseModel):
    machine_id: str | None = None
    name: str
    address: str | None = None
    status: str
    scanned_at: datetime | None = None
    summary: ScanSummary | None = None
    device_count: int = 0
    error: str | None = None
    executed_on: ExecutedOn


class FleetDevicesResponse(BaseModel):
    hosts: list[FleetHost]
    devices: list[dict[str, Any]]
    summary: ScanSummary
    generated_at: datetime


class DiscoverRequest(BaseModel):
    """LAN discovery scan parameters."""

    subnet: str | None = Field(
        default=None,
        description="Single CIDR subnet to scan, e.g. 192.168.0.0/24.",
    )
    subnets: list[str] | None = Field(
        default=None,
        description="Optional list of CIDR subnets (max 4).",
    )
    port: int = Field(default=8844, ge=1, le=65535, description="CDI API port to probe.")
    timeout_seconds: float = Field(
        default=1.5,
        ge=0.5,
        le=5.0,
        description="Per-host TCP/HTTP timeout in seconds.",
    )
    probe_token: str | None = Field(
        default=None,
        description=(
            "Optional X-API-Token sent (over plain HTTP) when probing remote CDI APIs. "
            "Omitted by default; this bench's own token is never sent."
        ),
    )


class DiscoveredHost(BaseModel):
    address: str
    ip: str
    port: int
    hostname: str | None = None
    # Remote /health payload as returned (includes auth_mode on newer APIs).
    health: dict[str, Any] | None = None
    cdi_api: bool = False
    already_registered: bool = False


class DiscoverResponse(BaseModel):
    scanned_subnets: list[str]
    port: int
    hosts_scanned: int
    open_ports: int
    found: list[DiscoveredHost]
    duration_ms: int
