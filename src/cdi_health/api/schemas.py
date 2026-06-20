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

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    """Scan request payload."""

    ignore_ata: bool = False
    ignore_nvme: bool = False
    ignore_scsi: bool = False
    device: str | None = None
    config: str | None = None
    mock_data: str | None = None
    mock_file: str | None = None
    machine_id: str | None = Field(
        default=None,
        description="Optional host registry ID to associate this scan with.",
    )


class ScanSummary(BaseModel):
    total: int
    healthy: int
    warning: int
    failed: int


class ScanResponse(BaseModel):
    scanned_at: datetime
    summary: ScanSummary
    devices: list[dict[str, Any]]


class ReportRequest(BaseModel):
    """Report generation request payload."""

    format: Literal["html", "pdf", "csv"] = "html"
    output_file: str | None = None
    ignore_ata: bool = False
    ignore_nvme: bool = False
    ignore_scsi: bool = False
    device: str | None = None
    config: str | None = None
    mock_data: str | None = None
    mock_file: str | None = None


class ReportResponse(BaseModel):
    generated_at: datetime
    output_file: str
    filename: str
    format: Literal["html", "pdf", "csv"]
    devices_count: int


class SelfTestStartRequest(BaseModel):
    """Start self-test job request payload."""

    device: str | None = Field(
        default=None,
        description="Single NVMe controller path, e.g. /dev/nvme0. If omitted, run on all supported devices.",
    )
    test_type: Literal["short", "extended"] = "short"
    wait: bool = False
    poll_interval_seconds: int = Field(default=30, ge=5, le=600)
    timeout_seconds: int = Field(default=14_400, ge=60, le=172_800)


class SelfTestAbortRequest(BaseModel):
    device: str


class HealthResponse(BaseModel):
    status: str
    is_root: bool
    allow_non_root_mode: bool
    api_token_enabled: bool
    missing_required_tools: list[str]
    weasyprint_available: bool
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


class MachineScanSummary(BaseModel):
    total: int
    healthy: int
    warning: int
    failed: int


class MachineCreate(BaseModel):
    """Register a grading host in the fleet registry."""

    name: str = Field(min_length=1, description="Display name shown in the dashboard.")
    hostname: str = Field(min_length=1, description="Host identifier, e.g. grading-01.local")
    address: str = Field(
        default="",
        description="Optional IP or host:port for a remote CDI API agent (future).",
    )
    location: str = Field(default="", description="Optional rack or data-center location label.")
    notes: str = ""


class MachineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    hostname: str | None = Field(default=None, min_length=1)
    address: str | None = None
    location: str | None = None
    notes: str | None = None
    status: Literal["unknown", "reachable", "unreachable"] | None = None


class MachineResponse(BaseModel):
    id: str
    name: str
    hostname: str
    address: str
    location: str
    notes: str
    status: Literal["unknown", "reachable", "unreachable"]
    last_seen_at: datetime | None = None
    last_scan_at: datetime | None = None
    last_scan_status: Literal["success", "failed"] | None = None
    last_scan_summary: MachineScanSummary | None = None
    created_at: datetime
    updated_at: datetime


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
        description="Optional X-API-Token sent when probing remote CDI APIs.",
    )


class DiscoveredHost(BaseModel):
    address: str
    ip: str
    port: int
    hostname: str | None = None
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
