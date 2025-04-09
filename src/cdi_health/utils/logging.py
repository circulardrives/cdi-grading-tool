"""
Logging Utilities

This module provides logging configuration for the application.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

def setup_logging(debug: bool = False, quiet: bool = False) -> None:
    """Configure logging for the application."""
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(console_handler)

    # Set quiet mode
    if quiet:
        root_logger.setLevel(logging.WARNING)

    # Configure third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)