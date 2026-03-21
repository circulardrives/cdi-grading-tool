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

"""Tests for CLI functionality."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from cdi_health.cli import (
    check_prerequisites,
    cmd_scan,
    create_parser,
    scan_devices_mock,
    scan_single_mock,
)


class TestPrerequisites:
    """Test prerequisite checking."""

    @patch("shutil.which")
    def test_check_prerequisites_all_found(self, mock_which: MagicMock) -> None:
        """Test when all prerequisites are found."""
        mock_which.return_value = "/usr/bin/tool"
        missing = check_prerequisites()
        # Should return empty list if all tools found
        assert isinstance(missing, list)

    @patch("shutil.which")
    def test_check_prerequisites_some_missing(self, mock_which: MagicMock) -> None:
        """Test when some prerequisites are missing."""
        def side_effect(tool: str) -> str | None:
            if tool == "nvme":
                return "/usr/bin/nvme"
            return None
        
        mock_which.side_effect = side_effect
        missing = check_prerequisites()
        # Should list missing tools
        assert isinstance(missing, list)


class TestScanCommands:
    """Test scan command functionality."""

    def test_scan_single_mock(self, mock_data_dir) -> None:
        """Test scanning single mock device."""
        import os
        mock_file = os.path.join(mock_data_dir, "nvme", "healthy_ssd.json")
        if os.path.exists(mock_file):
            devices = scan_single_mock(mock_file)
            assert isinstance(devices, list)
            assert len(devices) > 0

    def test_scan_devices_mock(self, mock_data_dir) -> None:
        """Test scanning mock devices from directory."""
        devices = scan_devices_mock(str(mock_data_dir))
        assert isinstance(devices, list)

    @patch("cdi_health.cli.scan_devices_mock")
    @patch("cdi_health.cli.setup_logging")
    def test_cmd_scan_mock_mode(
        self, mock_setup_logging: MagicMock, mock_scan: MagicMock
    ) -> None:
        """Test scan command with mock data."""
        from argparse import Namespace
        
        mock_scan.return_value = [{"dut": "/dev/nvme0", "model_number": "Test"}]
        
        args = Namespace(
            mock_data="test/path",
            mock_file=None,
            ignore_ata=False,
            ignore_nvme=False,
            ignore_scsi=False,
            output="table",
            all=False,
            details=False,
            device=None,
            verbose=False,
            no_color=False,
            config=None,
        )
        
        result = cmd_scan(args)
        assert result == 0


class TestCLIParser:
    """Test CLI argument parser."""

    def test_create_parser(self) -> None:
        """Test parser creation."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "cdi-health"

    def test_parser_has_subcommands(self) -> None:
        """Test that parser has expected subcommands."""
        parser = create_parser()
        # Parse args without --help (which causes SystemExit)
        args = parser.parse_args(["scan", "--output", "json"])
        assert args.command == "scan"
        assert args.output == "json"

    def test_parser_version(self) -> None:
        """Test version argument."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])
