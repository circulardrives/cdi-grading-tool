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

    format: Literal["html", "pdf"] = "html"
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
    format: Literal["html", "pdf"]
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

