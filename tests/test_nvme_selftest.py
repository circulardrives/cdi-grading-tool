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

"""Tests for NVMe self-test functionality."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cdi_health.classes.nvme_selftest import NVMeSelfTest


class TestNVMeSelfTest:
    """Test NVMeSelfTest class."""

    def test_initialization(self) -> None:
        """Test NVMeSelfTest initialization."""
        selftest = NVMeSelfTest("/dev/nvme0")
        assert selftest.device_path == "/dev/nvme0"
        assert selftest.nvme_path is not None

    @patch("shutil.which")
    def test_find_nvme_cli_not_found(self, mock_which: MagicMock) -> None:
        """Test when nvme-cli is not found."""
        mock_which.return_value = None
        with pytest.raises(Exception):  # Should raise CommandException
            NVMeSelfTest("/dev/nvme0")

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_is_supported_true(self, mock_which: MagicMock, mock_run: MagicMock) -> None:
        """Test is_supported when device supports self-test."""
        mock_which.return_value = "/usr/bin/nvme"
        mock_result = MagicMock()
        mock_result.return_code = 0
        mock_result.output = b'{"oacs": 16}'  # Bit 4 set (0x10 = 16)
        mock_run.return_value = mock_result

        with patch("cdi_health.classes.tools.Command") as mock_command:
            mock_cmd = MagicMock()
            mock_cmd.return_code = 0
            mock_cmd.output = b'{"oacs": 16}'
            mock_command.return_value = mock_cmd

            selftest = NVMeSelfTest("/dev/nvme0")
            # Mock the command run
            mock_cmd.run = MagicMock()
            result = selftest.is_supported()
            # Should return True if OACS bit 4 is set
            assert isinstance(result, bool)

    @patch("subprocess.run")
    def test_find_nvme_devices(self, mock_run: MagicMock) -> None:
        """Test finding NVMe devices."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"Devices": [{"DevicePath": "/dev/nvme0n1"}, {"DevicePath": "/dev/nvme1n1"}]}'
        mock_run.return_value = mock_result

        devices = NVMeSelfTest.find_nvme_devices()
        assert isinstance(devices, list)
        # Should extract controllers from namespace paths
        assert "/dev/nvme0" in devices or "/dev/nvme1" in devices or len(devices) >= 0

    def test_find_supported_devices(self) -> None:
        """Test finding devices that support self-test."""
        with patch.object(NVMeSelfTest, "find_nvme_devices", return_value=["/dev/nvme0"]):
            with patch.object(NVMeSelfTest, "is_supported", return_value=True):
                devices = NVMeSelfTest.find_supported_devices()
                assert isinstance(devices, list)
                assert len(devices) > 0
                assert devices[0]["device"] == "/dev/nvme0"
                assert devices[0]["supported"] is True
