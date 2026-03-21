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

"""Tests for logging system."""

from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from cdi_health.logger import ColoredFormatter, get_logger, setup_logging


class TestLogger:
    """Test logging functionality."""

    def test_get_logger(self) -> None:
        """Test getting a logger instance."""
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)
        assert logger.name == __name__

    def test_setup_logging_default(self) -> None:
        """Test setting up logging with default settings."""
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_setup_logging_verbose(self) -> None:
        """Test setting up logging with verbose mode."""
        setup_logging(verbose=True)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_no_color(self) -> None:
        """Test setting up logging without colors."""
        setup_logging(no_color=True)
        root_logger = logging.getLogger()
        # Should still work, just without colors
        assert root_logger.level == logging.INFO

    @patch("sys.stderr")
    def test_colored_formatter_with_tty(self, mock_stderr: MagicMock) -> None:
        """Test colored formatter with TTY."""
        mock_stderr.isatty.return_value = True
        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "test message" in formatted

    @patch("sys.stderr")
    def test_colored_formatter_without_tty(self, mock_stderr: MagicMock) -> None:
        """Test colored formatter without TTY."""
        mock_stderr.isatty.return_value = False
        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "test message" in formatted
