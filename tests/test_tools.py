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

"""Tests for tool path detection and command execution."""

from __future__ import annotations

import os
import shlex
import sys
from unittest.mock import MagicMock, patch

import pytest

from cdi_health.classes.tools import Command, SeaTools, SG3Utils, Smartctl


def _python_cmd(code: str) -> str:
    """Return a cross-platform command for Command's shell-free execution path."""
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"


class TestCommand:
    """Test Command class."""

    def test_command_initialization(self) -> None:
        """Test command initialization."""
        cmd = Command("echo test")
        assert cmd.command == "echo test"

    def test_command_execution_success(self) -> None:
        """Test successful command execution."""
        cmd = Command(_python_cmd("print('test')"))
        cmd.run()
        assert cmd.return_code == 0
        assert b"test" in cmd.output

    def test_command_execution_failure(self) -> None:
        """Test failed command execution."""
        cmd = Command(_python_cmd("import sys; sys.exit(1)"))
        cmd.run()
        assert cmd.return_code != 0

    def test_get_return_code(self) -> None:
        """Test get_return_code method."""
        cmd = Command(_python_cmd("import sys; sys.exit(0)"))
        cmd.run()
        assert cmd.get_return_code() == 0

    def test_has_errors(self) -> None:
        """Test has_errors method."""
        cmd = Command(_python_cmd("import sys; sys.exit(1)"))
        cmd.run()
        # false command may or may not have stderr output
        assert isinstance(cmd.has_errors(), bool)


class TestSeaTools:
    """Test SeaTools path detection."""

    def test_seatools_initialization(self) -> None:
        """Test SeaTools initialization."""
        tools = SeaTools("/dev/sda")
        assert tools.dut == "/dev/sda"
        assert hasattr(tools, "seachest_basics_path")
        assert hasattr(tools, "seachest_smart_path")

    @patch("shutil.which")
    def test_get_seachest_path_from_path(self, mock_which: MagicMock) -> None:
        """Test finding openSeaChest via PATH."""
        mock_which.return_value = "/usr/local/bin/openSeaChest_Basics"
        # Create tools instance (will call get_seachest_path during init)
        tools = SeaTools("/dev/sda")
        # Now test the method directly
        path = tools.get_seachest_path("openSeaChest_Basics")
        assert path == "/usr/local/bin/openSeaChest_Basics"
        # Should have been called (at least once during init and once in test)
        assert mock_which.called

    @patch("shutil.which")
    @patch("os.path.exists")
    @patch("os.access")
    def test_get_seachest_path_from_standard_path(
        self, mock_access: MagicMock, mock_exists: MagicMock, mock_which: MagicMock
    ) -> None:
        """Test finding openSeaChest in standard installation path."""
        mock_which.return_value = None
        mock_exists.return_value = True
        mock_access.return_value = True

        tools = SeaTools("/dev/sda")
        path = tools.get_seachest_path("openSeaChest_Basics")

        # Should check standard paths
        assert mock_exists.called
        # Should return a path (either found or fallback to tool name)
        assert isinstance(path, str)

    @patch("shutil.which")
    @patch("os.path.exists")
    @patch("os.access")
    def test_get_seachest_path_fallback(
        self, mock_access: MagicMock, mock_exists: MagicMock, mock_which: MagicMock
    ) -> None:
        """Test fallback to tool name when not found."""
        mock_which.return_value = None
        mock_exists.return_value = False  # Path doesn't exist

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            tools = SeaTools("/dev/sda")
            path = tools.get_seachest_path("openSeaChest_Basics")
            # Should fallback to tool name when nothing found
            assert path == "openSeaChest_Basics"


class TestSmartctl:
    """Test Smartctl path detection."""

    def test_smartctl_initialization(self) -> None:
        """Test Smartctl initialization."""
        smartctl = Smartctl("/dev/sda")
        assert smartctl.dut == "/dev/sda"
        assert hasattr(smartctl, "smartctl_path")

    @patch("shutil.which")
    def test_get_smartctl_path_from_path(self, mock_which: MagicMock) -> None:
        """Test finding smartctl via PATH."""
        mock_which.return_value = "/usr/sbin/smartctl"
        smartctl = Smartctl("/dev/sda")
        path = smartctl.get_smartctl_path()
        assert path == "/usr/sbin/smartctl"

    @patch("shutil.which")
    def test_get_smartctl_path_fallback(self, mock_which: MagicMock) -> None:
        """Test fallback to 'smartctl' when not found."""
        mock_which.return_value = None

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            smartctl = Smartctl("/dev/sda")
            path = smartctl.get_smartctl_path()
            assert path == "smartctl"


class TestSG3Utils:
    """Test SG3Utils path detection."""

    def test_sg3utils_initialization(self) -> None:
        """Test SG3Utils initialization."""
        sg3 = SG3Utils("/dev/sg0")
        assert sg3.dut == "/dev/sg0"
        assert hasattr(sg3, "sg_map26_path")
        assert hasattr(sg3, "sg_turs_path")

    @patch("shutil.which")
    def test_get_sg3utils_path_from_path(self, mock_which: MagicMock) -> None:
        """Test finding sg3_utils tools via PATH."""
        mock_which.return_value = "/usr/bin/sg_map26"
        sg3 = SG3Utils("/dev/sg0")
        path = sg3.get_sg3utils_path("sg_map26")
        assert path == "/usr/bin/sg_map26"
