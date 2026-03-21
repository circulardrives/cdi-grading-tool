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

"""
Terminal Colors and Styling for CDI Health

Provides ANSI color codes and styling utilities for terminal output.
"""

from __future__ import annotations

import os
import sys


class Colors:
    """ANSI color codes for terminal output."""

    # Basic colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Reset
    RESET = "\033[0m"

    # Class state
    _enabled = True

    @classmethod
    def disable(cls) -> None:
        """Disable color output."""
        cls._enabled = False

    @classmethod
    def enable(cls) -> None:
        """Enable color output."""
        cls._enabled = True

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if colors are enabled."""
        return cls._enabled

    @classmethod
    def auto_detect(cls) -> None:
        """Auto-detect if terminal supports colors."""
        # Disable colors if:
        # - NO_COLOR environment variable is set
        # - TERM is "dumb"
        # - stdout is not a TTY
        if os.environ.get("NO_COLOR"):
            cls._enabled = False
        elif os.environ.get("TERM") == "dumb":
            cls._enabled = False
        elif not sys.stdout.isatty():
            cls._enabled = False
        else:
            cls._enabled = True

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """
        Apply color to text.

        :param text: Text to colorize
        :param color: Color code to apply
        :return: Colorized text (or plain text if colors disabled)
        """
        if not cls._enabled:
            return text
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def bold(cls, text: str) -> str:
        """Make text bold."""
        return cls.colorize(text, cls.BOLD)

    @classmethod
    def dim(cls, text: str) -> str:
        """Make text dim."""
        return cls.colorize(text, cls.DIM)

    @classmethod
    def red(cls, text: str) -> str:
        """Make text red."""
        return cls.colorize(text, cls.BRIGHT_RED)

    @classmethod
    def green(cls, text: str) -> str:
        """Make text green."""
        return cls.colorize(text, cls.BRIGHT_GREEN)

    @classmethod
    def yellow(cls, text: str) -> str:
        """Make text yellow."""
        return cls.colorize(text, cls.BRIGHT_YELLOW)

    @classmethod
    def blue(cls, text: str) -> str:
        """Make text blue."""
        return cls.colorize(text, cls.BRIGHT_BLUE)

    @classmethod
    def cyan(cls, text: str) -> str:
        """Make text cyan."""
        return cls.colorize(text, cls.BRIGHT_CYAN)

    @classmethod
    def magenta(cls, text: str) -> str:
        """Make text magenta."""
        return cls.colorize(text, cls.BRIGHT_MAGENTA)

    @classmethod
    def grade_color(cls, grade: str) -> str:
        """
        Get color code for a grade.

        :param grade: Letter grade (A, B, C, D, F)
        :return: ANSI color code
        """
        colors = {
            "A": cls.BRIGHT_GREEN,
            "B": cls.GREEN,
            "C": cls.YELLOW,
            "D": cls.BRIGHT_YELLOW,
            "F": cls.BRIGHT_RED,
        }
        return colors.get(grade.upper(), cls.WHITE)

    @classmethod
    def score_color(cls, score: int) -> str:
        """
        Get color code for a numeric score.

        :param score: Numeric score 0-100
        :return: ANSI color code
        """
        if score >= 90:
            return cls.BRIGHT_GREEN
        elif score >= 75:
            return cls.GREEN
        elif score >= 60:
            return cls.YELLOW
        elif score >= 40:
            return cls.BRIGHT_YELLOW
        else:
            return cls.BRIGHT_RED

    @classmethod
    def severity_color(cls, severity: str) -> str:
        """
        Get color code for a severity level.

        :param severity: Severity level (info, warning, critical)
        :return: ANSI color code
        """
        colors = {
            "info": cls.BRIGHT_BLUE,
            "warning": cls.BRIGHT_YELLOW,
            "critical": cls.BRIGHT_RED,
        }
        return colors.get(severity.lower(), cls.WHITE)

    @classmethod
    def format_grade(cls, grade: str) -> str:
        """Format a grade with appropriate color."""
        color = cls.grade_color(grade)
        return cls.colorize(grade, color + cls.BOLD)

    @classmethod
    def format_score(cls, score: int) -> str:
        """Format a score with appropriate color."""
        color = cls.score_color(score)
        return cls.colorize(str(score), color + cls.BOLD)

    @classmethod
    def format_status(cls, status: str, is_healthy: bool) -> str:
        """Format status text with icon and color."""
        if is_healthy:
            icon = "✓"
            color = cls.BRIGHT_GREEN
        elif status.lower() in ("warning", "fair", "poor"):
            icon = "⚠"
            color = cls.BRIGHT_YELLOW
        else:
            icon = "✗"
            color = cls.BRIGHT_RED

        return cls.colorize(f"{icon} {status}", color)


class Symbols:
    """Unicode symbols for terminal output."""

    # Status icons
    CHECK = "✓"
    CROSS = "✗"
    WARNING = "⚠"
    INFO = "ℹ"
    ARROW_RIGHT = "→"
    ARROW_LEFT = "←"
    BULLET = "•"

    # Box drawing (heavy)
    BOX_H = "═"
    BOX_V = "║"
    BOX_TL = "╔"
    BOX_TR = "╗"
    BOX_BL = "╚"
    BOX_BR = "╝"
    BOX_VL = "╠"
    BOX_VR = "╣"
    BOX_HT = "╦"
    BOX_HB = "╩"
    BOX_CROSS = "╬"

    # Box drawing (light)
    BOX_H_LIGHT = "─"
    BOX_V_LIGHT = "│"
    BOX_TL_LIGHT = "┌"
    BOX_TR_LIGHT = "┐"
    BOX_BL_LIGHT = "└"
    BOX_BR_LIGHT = "┘"
    BOX_VL_LIGHT = "├"
    BOX_VR_LIGHT = "┤"
    BOX_HT_LIGHT = "┬"
    BOX_HB_LIGHT = "┴"
    BOX_CROSS_LIGHT = "┼"

    @classmethod
    def status_icon(cls, status: str) -> str:
        """Get icon for a status."""
        status_lower = status.lower()
        if status_lower in ("healthy", "excellent", "good", "pass", "passed", "a", "b"):
            return cls.CHECK
        elif status_lower in ("warning", "fair", "c", "d"):
            return cls.WARNING
        else:
            return cls.CROSS

    @classmethod
    def severity_icon(cls, severity: str) -> str:
        """Get icon for a severity level."""
        severity_lower = severity.lower()
        if severity_lower == "info":
            return cls.INFO
        elif severity_lower == "warning":
            return cls.WARNING
        else:
            return cls.CROSS
