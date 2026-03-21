#
# Copyright (c) 2025 Circular Drive Initiative.
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

"""Pytest configuration and fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def mock_data_dir() -> Path:
    """Return path to mock data directory."""
    return Path(__file__).parent.parent / "src" / "cdi_health" / "mock_data"


@pytest.fixture
def sample_nvme_device(mock_data_dir: Path) -> dict[str, Any]:
    """Load sample NVMe device data."""
    device_file = mock_data_dir / "nvme" / "healthy_ssd.json"
    if not device_file.exists():
        # Fallback to any available NVMe device
        nvme_dir = mock_data_dir / "nvme"
        device_file = next(nvme_dir.glob("*.json"), None)
        if device_file is None:
            pytest.skip("No mock NVMe device data available")
    
    with device_file.open() as f:
        return json.load(f)


@pytest.fixture
def sample_ata_device(mock_data_dir: Path) -> dict[str, Any]:
    """Load sample ATA device data."""
    device_file = mock_data_dir / "ata" / "healthy_hdd.json"
    if not device_file.exists():
        # Fallback to any available ATA device
        ata_dir = mock_data_dir / "ata"
        device_file = next(ata_dir.glob("*.json"), None)
        if device_file is None:
            pytest.skip("No mock ATA device data available")
    
    with device_file.open() as f:
        return json.load(f)


@pytest.fixture
def sample_scsi_device(mock_data_dir: Path) -> dict[str, Any]:
    """Load sample SCSI device data."""
    device_file = mock_data_dir / "scsi" / "healthy_sas.json"
    if not device_file.exists():
        pytest.skip("No mock SCSI device data available")
    
    with device_file.open() as f:
        return json.load(f)
