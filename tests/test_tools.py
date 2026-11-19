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

import pytest

from cdi_health.classes import tools
from cdi_health.classes.exceptions import CommandException
from cdi_health.classes.tools import Command, SG3Utils, Smartctl, nvme_controller_name, nvme_readiness


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

    @patch("shutil.which", return_value="/usr/sbin/smartctl")
    def test_default_command_has_no_device_type(self, _mock_which: MagicMock) -> None:
        smartctl = Smartctl("/dev/sda")
        assert smartctl.device_type is None
        assert smartctl.get_all_device_information_command == "sudo /usr/sbin/smartctl --xall"

    @patch("shutil.which", return_value="/usr/sbin/smartctl")
    def test_device_type_adds_d_flag(self, _mock_which: MagicMock) -> None:
        """Synology /dev/sataN disks are opened with -d sat."""
        smartctl = Smartctl("/dev/sata1", device_type="sat")
        assert smartctl.get_all_device_information_command == "sudo /usr/sbin/smartctl -d sat --xall"

    @pytest.mark.parametrize("bad", ["sat --set=standby,now", "-d", "SAT", "sat;reboot", ""])
    def test_invalid_device_type_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            Smartctl("/dev/sata1", device_type=bad)


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


class TestNvmeReadiness:
    """#162: NVMe readiness is the kernel's controller state, never a translated SCSI TUR."""

    @staticmethod
    def _sysfs(tmp_path, monkeypatch, states: dict[str, str]):
        for controller, state in states.items():
            directory = tmp_path / controller
            directory.mkdir()
            (directory / "state").write_text(f"{state}\n", encoding="utf-8")
        monkeypatch.setattr(tools, "NVME_SYSFS_ROOT", tmp_path)

    @pytest.mark.parametrize(
        ("device", "controller"),
        [
            ("/dev/nvme0", "nvme0"),
            ("/dev/nvme0n1", "nvme0"),
            ("/dev/nvme12n3p2", "nvme12"),
            ("/dev/sda", None),
            ("/dev/sg3", None),
        ],
    )
    def test_controller_name(self, device: str, controller: str | None) -> None:
        assert nvme_controller_name(device) == controller

    @pytest.mark.parametrize(
        ("state", "expected"),
        [
            ("live", "Ready"),
            ("LIVE", "Ready"),
            ("dead", "Not Ready"),
            # Transitional states say nothing about the drive's health.
            ("resetting", "Unknown"),
            ("connecting", "Unknown"),
            ("deleting", "Unknown"),
            ("new", "Unknown"),
            ("", "Unknown"),
        ],
    )
    def test_controller_state(self, tmp_path, monkeypatch, state: str, expected: str) -> None:
        self._sysfs(tmp_path, monkeypatch, {"nvme0": state})
        assert nvme_readiness("/dev/nvme0") == expected
        assert nvme_readiness("/dev/nvme0n1") == expected

    def test_each_drive_reads_its_own_controller(self, tmp_path, monkeypatch) -> None:
        self._sysfs(tmp_path, monkeypatch, {"nvme0": "live", "nvme1": "dead"})
        assert nvme_readiness("/dev/nvme0n1") == "Ready"
        assert nvme_readiness("/dev/nvme1n1") == "Not Ready"

    def test_no_sysfs_entry_is_unknown(self, tmp_path, monkeypatch) -> None:
        """No sysfs (some containers, non-Linux) is not evidence of a bad drive."""
        self._sysfs(tmp_path, monkeypatch, {})
        assert nvme_readiness("/dev/nvme0") == "Unknown"

    def test_nvme_is_never_sent_a_scsi_tur(self, tmp_path, monkeypatch) -> None:
        """No sg_turs / sg_start process is started for an NVMe drive."""
        self._sysfs(tmp_path, monkeypatch, {"nvme2": "live"})

        class ForbiddenCommand:
            def __init__(self, command, **_kwargs):
                raise AssertionError(f"NVMe readiness ran a subprocess: {command}")

        with patch("cdi_health.classes.tools.Command", ForbiddenCommand):
            assert SG3Utils("/dev/nvme2").test_unit_ready() == "Ready"
            assert SG3Utils("/dev/nvme2n1").test_unit_ready() == "Ready"

    def test_sata_and_sas_still_use_tur(self, tmp_path, monkeypatch) -> None:
        self._sysfs(tmp_path, monkeypatch, {})
        calls: list = []

        class FakeCommand:
            def __init__(self, command, **_kwargs):
                calls.append(command)

            def run(self):
                return None

            def get_return_code(self):
                return 0

        with patch("cdi_health.classes.tools.Command", FakeCommand):
            assert SG3Utils("/dev/sg0").test_unit_ready() == "Ready"
        # (The tool path itself is cached per process, so only check the device.)
        assert len(calls) == 1 and calls[0].endswith("-vvvv /dev/sg0")
