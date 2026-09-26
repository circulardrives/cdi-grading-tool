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

import shlex
import sys
from unittest.mock import MagicMock, patch

from cdi_health.classes.exceptions import CommandException
from cdi_health.classes.tools import Command, SG3Utils, Smartctl


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

    @patch("os.path.exists", return_value=False)
    @patch("shutil.which", return_value=None)
    def test_get_smartctl_path_fallback(self, mock_which: MagicMock, mock_exists: MagicMock) -> None:
        """Test fallback to 'smartctl' when not on PATH or in common install dirs."""
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
        SG3Utils._path_cache.clear()
        mock_which.return_value = "/usr/bin/sg_map26"
        sg3 = SG3Utils("/dev/sg0")
        path = sg3.get_sg3utils_path("sg_map26")
        assert path == "/usr/bin/sg_map26"


class TestTestUnitReady:
    """TEST UNIT READY classification and retry (#128)."""

    @staticmethod
    def _fake_command(outcomes: list, calls: list):
        """Build a Command stand-in; each outcome is a return code or an exception."""

        class FakeCommand:
            def __init__(self, command: str = None, timeout=None) -> None:
                self.command = command
                self.return_code = None

            def run(self) -> None:
                calls.append(self.command)
                if "--start" in self.command:
                    self.return_code = 0
                    return
                outcome = outcomes.pop(0)
                if isinstance(outcome, Exception):
                    raise outcome
                self.return_code = outcome

            def get_return_code(self):
                return self.return_code

        return FakeCommand

    def _tur(self, outcomes: list) -> tuple[str, list]:
        calls: list = []
        with patch("cdi_health.classes.tools.Command", self._fake_command(outcomes, calls)):
            state = SG3Utils("/dev/sg0").test_unit_ready()
        return state, calls

    def test_ready(self) -> None:
        state, calls = self._tur([0])
        assert state == "Ready"
        assert len(calls) == 1

    def test_tool_missing_is_unknown_not_not_ready(self) -> None:
        state, calls = self._tur([CommandException("Command not found")])
        assert state == "Unknown"
        assert len(calls) == 1  # no retry for tool errors

    def test_timeout_is_unknown(self) -> None:
        state, _ = self._tur([CommandException("Command timed out after 30s")])
        assert state == "Unknown"

    def test_sudo_or_syntax_error_is_unknown(self) -> None:
        # sudo password prompt failure / sg_turs syntax error both exit 1
        state, _ = self._tur([1])
        assert state == "Unknown"

    def test_device_open_failure_is_unknown(self) -> None:
        state, _ = self._tur([15])
        assert state == "Unknown"

    def test_genuine_not_ready_retried_then_reported(self) -> None:
        state, calls = self._tur([2, 2])
        assert state == "Not Ready"
        tur_calls = [c for c in calls if "--start" not in c]
        assert len(tur_calls) == 2
        assert any("--start" in c for c in calls)

    def test_not_ready_that_recovers_on_retry_is_ready(self) -> None:
        state, _ = self._tur([2, 0])
        assert state == "Ready"

    def test_not_ready_then_tool_error_is_unknown(self) -> None:
        state, _ = self._tur([2, 99])
        assert state == "Unknown"

    def test_medium_hardware_error_is_not_ready(self) -> None:
        state, _ = self._tur([3, 3])
        assert state == "Not Ready"
