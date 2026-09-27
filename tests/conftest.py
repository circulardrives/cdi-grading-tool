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

"""Pytest configuration and fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cdi_health.classes.config import ThresholdConfig


@pytest.fixture(autouse=True, scope="session")
def _no_real_sudo(tmp_path_factory: pytest.TempPathFactory) -> None:
    """
    Shadow ``sudo`` with a stub that fails immediately.

    Tests must never reach real hardware tools; on a dev laptop a real sudo
    pops a password / Touch ID prompt that blocks the run (and any agent).
    """
    import os

    stub_dir = tmp_path_factory.mktemp("no-sudo")
    stub = stub_dir / "sudo"
    stub.write_text('#!/bin/sh\necho "tests: real sudo is disabled: $*" >&2\nexit 1\n', encoding="utf-8")
    stub.chmod(0o755)
    previous = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{stub_dir}{os.pathsep}{previous}"
    yield
    os.environ["PATH"] = previous


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Refuse outbound HTTP connections to anything but loopback.

    Adding a bench probes its address once (to catch "this bench itself"), so
    tests that register made-up LAN addresses must fail fast instead of
    reaching (or waiting on) a real network. Fake benches listen on 127.0.0.1.
    """
    import socket

    real_create_connection = socket.create_connection

    def guarded(address, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        host = str(address[0])
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ConnectionRefusedError(f"tests: outbound connection to {host} is disabled")
        return real_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", guarded)


@pytest.fixture(autouse=True)
def _reset_threshold_config() -> None:
    """Isolate grading.profile mutations across tests (binary vs abcdf)."""
    ThresholdConfig.reset_instance()
    yield
    ThresholdConfig.reset_instance()


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
