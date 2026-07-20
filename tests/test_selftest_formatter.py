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

"""Tests for self-test formatter."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cdi_health.classes.selftest_formatter import SelfTestFormatter


class TestSelfTestFormatter:
    """Test SelfTestFormatter."""

    def test_format_empty_results(self) -> None:
        """Test formatting empty results."""
        formatter = SelfTestFormatter()
        result = formatter.format_summary([])
        assert "No devices found" in result or "No devices" in result

    def test_format_single_result(self) -> None:
        """Test formatting single test result."""
        formatter = SelfTestFormatter()
        results = [
            {
                "device": "/dev/nvme0",
                "model": "Test SSD",
                "supported": True,
                "test_type": "short",
                "test_started": True,
                "test_completed": True,
                "test_passed": True,
                "test_failed": False,
                "test_in_progress": False,
                "test_error": None,
                "last_test_date": None,
            }
        ]
        result = formatter.format_summary(results)
        assert "/dev/nvme0" in result
        assert "Test SSD" in result

    def test_format_multiple_results(self) -> None:
        """Test formatting multiple test results."""
        formatter = SelfTestFormatter()
        results = [
            {
                "device": "/dev/nvme0",
                "model": "Test SSD 1",
                "supported": True,
                "test_type": "short",
                "test_started": True,
                "test_completed": True,
                "test_passed": True,
                "test_failed": False,
                "test_in_progress": False,
                "test_error": None,
                "last_test_date": None,
            },
            {
                "device": "/dev/nvme1",
                "model": "Test SSD 2",
                "supported": False,
                "test_type": "-",
                "test_started": False,
                "test_completed": False,
                "test_passed": False,
                "test_failed": False,
                "test_in_progress": False,
                "test_error": None,
                "last_test_date": None,
            },
        ]
        result = formatter.format_summary(results)
        assert "/dev/nvme0" in result
        assert "/dev/nvme1" in result

    @patch("shutil.get_terminal_size")
    def test_terminal_width_detection(self, mock_terminal_size) -> None:
        """Test terminal width detection."""
        from unittest.mock import MagicMock

        mock_terminal_size.return_value = MagicMock(columns=80)

        formatter = SelfTestFormatter()
        assert formatter.terminal_width == 80

    @patch("shutil.get_terminal_size")
    def test_terminal_width_fallback(self, mock_terminal_size) -> None:
        """Test terminal width fallback."""
        import os

        mock_terminal_size.side_effect = OSError()

        # Test with COLUMNS env var
        with patch.dict(os.environ, {"COLUMNS": "120"}):
            formatter = SelfTestFormatter()
            assert formatter.terminal_width == 120

    def test_format_test_status_running(self) -> None:
        """Test formatting running test status."""
        formatter = SelfTestFormatter()
        result = {
            "test_in_progress": True,
            "test_started": True,
        }
        status = formatter._format_test_status(result)
        assert "Running" in status or "⏳" in status

    def test_format_test_status_completed(self) -> None:
        """Test formatting completed test status."""
        formatter = SelfTestFormatter()
        result = {
            "test_completed": True,
            "test_passed": True,
        }
        status = formatter._format_test_status(result)
        assert "Complete" in status or "✓" in status

    def test_format_test_result_passed(self) -> None:
        """Test formatting passed test result."""
        formatter = SelfTestFormatter()
        result = {
            "test_passed": True,
        }
        test_result = formatter._format_test_result(result)
        assert "Passed" in test_result or "✓" in test_result

    def test_format_test_result_failed(self) -> None:
        """Test formatting failed test result."""
        formatter = SelfTestFormatter()
        result = {
            "test_failed": True,
        }
        test_result = formatter._format_test_result(result)
        assert "Failed" in test_result or "✗" in test_result

    def test_align_text_pads_ansi_colored_cells(self) -> None:
        """ANSI color codes must not shrink column padding (issue #113)."""
        from cdi_health.classes.colors import Colors

        formatter = SelfTestFormatter()
        colored = Colors.green("✓ Complete")
        plain = "○ Ready"
        width = 14

        aligned_colored = formatter._align_text(colored, width)
        aligned_plain = formatter._align_text(plain, width)

        assert formatter._display_width(aligned_colored) == width
        assert formatter._display_width(aligned_plain) == width
        # Trailing pad spaces are outside the ANSI wrap
        assert aligned_colored.endswith(" " * (width - formatter._display_width(colored)))

    def test_full_table_columns_align_with_unicode_status(self) -> None:
        """Full-layout body columns stay aligned when status/result use ✓."""
        import os
        import re

        from cdi_health.classes.colors import Colors

        Colors.enable()
        with patch.dict(os.environ, {"COLUMNS": "160"}):
            formatter = SelfTestFormatter()

        results = [
            {
                "device": "/dev/nvme0",
                "model": "INTEL SSDPEKKW010T8",
                "serial": "PHHH829001YN1P0E",
                "supported": True,
                "test_type": "Short",
                "test_started": True,
                "test_completed": True,
                "test_passed": True,
                "test_failed": False,
                "test_in_progress": False,
                "test_error": None,
                "last_test_date": None,
            },
            {
                "device": "/dev/nvme1",
                "model": "KXG60PNV2T04 TOSHIBA",
                "serial": "59LF701SF91N",
                "supported": True,
                "test_type": "short",
                "test_started": False,
                "test_completed": False,
                "test_passed": False,
                "test_failed": False,
                "test_in_progress": False,
                "test_error": None,
                "last_test_date": None,
            },
        ]
        output = formatter.format_summary(results)
        # Prefer full layout at COLUMNS=160
        assert "Test Status" in output

        ansi = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        data_rows = [
            line
            for line in output.splitlines()
            if line.startswith("│ /dev/nvme")
        ]
        assert len(data_rows) == 2

        # All data rows and the header row must share the same display width
        header_row = next(line for line in output.splitlines() if "Test Status" in line)
        header_w = formatter._display_width(ansi.sub("", header_row))
        for row in data_rows:
            assert formatter._display_width(ansi.sub("", row)) == header_w

        # Test Type casing normalized (short -> Short)
        assert "Short" in output
        assert not re.search(r"│\s+short\s+│", ansi.sub("", output))

    def test_normalize_test_type_casing(self) -> None:
        """Test type labels are title-cased for display."""
        assert SelfTestFormatter._normalize_test_type("short") == "Short"
        assert SelfTestFormatter._normalize_test_type("Short") == "Short"
        assert SelfTestFormatter._normalize_test_type("extended") == "Extended"
        assert SelfTestFormatter._normalize_test_type("-") == "-"
        assert SelfTestFormatter._normalize_test_type(None) == "-"
