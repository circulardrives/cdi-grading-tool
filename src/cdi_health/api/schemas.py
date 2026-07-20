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

from pydantic import BaseModel, Field, ValidationInfo, field_validator

# Strict NVMe controller/namespace paths only (no whitespace or extra tokens).
NVME_DEVICE_PATTERN = re.compile(r"^/dev/nvme[0-9]+(n[0-9]+)?$")
# Block-device style paths for scan/report filters (no shell metacharacters).
BLOCK_DEVICE_PATTERN = re.compile(r"^/dev/[a-zA-Z0-9][a-zA-Z0-9._+/-]*$")


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


class ScanResponse(BaseModel):
    scanned_at: datetime
    summary: ScanSummary
    devices: list[dict[str, Any]]


class HistorySummary(BaseModel):
    """Lightweight scan-history list entry (no device payloads)."""

    id: str
    scanned_at: datetime
    created_at: datetime | None = None
    machine_id: str | None = None
    mock: bool = False
    device_count: int
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
    summary: ScanSummary
    grades: dict[str, int] = Field(default_factory=dict)
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

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str | None) -> str | None:
        return _validate_optional_block_device(value)

    @field_validator("config", "mock_data", "mock_file", "output_file")
    @classmethod
    def validate_paths(cls, value: str | None, info: ValidationInfo) -> str | None:
        return _validate_optional_fs_path(value, info.field_name)


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

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str | None) -> str | None:
        return _validate_optional_nvme_device(value)


class SelfTestAbortRequest(BaseModel):
    device: str

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str) -> str:
        return _validate_required_nvme_device(value)


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    is_root: bool | None = None
    allow_non_root_mode: bool | None = None
    api_token_enabled: bool | None = None
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
