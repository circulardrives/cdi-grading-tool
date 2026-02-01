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

"""Tests for color and formatting utilities."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from cdi_health.classes.colors import Colors, Symbols


class TestColors:
    """Test Colors class."""

    def test_bold(self) -> None:
        """Test bold formatting."""
        result = Colors.bold("test")
        assert "test" in result

    def test_red(self) -> None:
        """Test red color."""
        result = Colors.red("test")
        assert "test" in result

    def test_green(self) -> None:
        """Test green color."""
        result = Colors.green("test")
        assert "test" in result

    def test_yellow(self) -> None:
        """Test yellow color."""
        result = Colors.yellow("test")
        assert "test" in result

    def test_disable_enable(self) -> None:
        """Test disabling and enabling colors."""
        Colors.disable()
        assert Colors.is_enabled() is False
        Colors.enable()
        assert Colors.is_enabled() is True

    @patch.dict(os.environ, {"NO_COLOR": "1"})
    def test_auto_detect_no_color_env(self) -> None:
        """Test auto-detection with NO_COLOR environment variable."""
        Colors.auto_detect()
        assert Colors.is_enabled() is False

    def test_grade_color(self) -> None:
        """Test grade color mapping."""
        color_a = Colors.grade_color("A")
        color_f = Colors.grade_color("F")
        assert color_a != color_f

    def test_score_color(self) -> None:
        """Test score color mapping."""
        color_100 = Colors.score_color(100)
        color_0 = Colors.score_color(0)
        assert color_100 != color_0

    def test_severity_color(self) -> None:
        """Test severity color mapping."""
        color_info = Colors.severity_color("info")
        color_critical = Colors.severity_color("critical")
        assert color_info != color_critical

    def test_format_grade(self) -> None:
        """Test grade formatting."""
        result = Colors.format_grade("A")
        assert "A" in result

    def test_format_score(self) -> None:
        """Test score formatting."""
        result = Colors.format_score(100)
        assert "100" in result


class TestSymbols:
    """Test Symbols class."""

    def test_status_icon_healthy(self) -> None:
        """Test status icon for healthy status."""
        icon = Symbols.status_icon("healthy")
        assert icon in (Symbols.CHECK, Symbols.WARNING, Symbols.CROSS)

    def test_status_icon_failed(self) -> None:
        """Test status icon for failed status."""
        icon = Symbols.status_icon("failed")
        assert icon == Symbols.CROSS

    def test_severity_icon(self) -> None:
        """Test severity icon mapping."""
        icon_info = Symbols.severity_icon("info")
        icon_warning = Symbols.severity_icon("warning")
        icon_critical = Symbols.severity_icon("critical")
        assert icon_info == Symbols.INFO
        assert icon_warning == Symbols.WARNING
        assert icon_critical == Symbols.CROSS
