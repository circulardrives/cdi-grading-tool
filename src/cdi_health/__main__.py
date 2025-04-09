#
# Copyright (c) 2025 Circular Drive Initiative.
#
# This file is part of CDI Health.
# See https://github.com/circulardrives/cdi-grading-tool-alpha/ for further info.
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

#!/usr/bin/env python3
"""
CDI Health CLI Tool

This is the main entry point for the CDI Health CLI tool.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from cdi_health.core.device_manager import DeviceManager
from cdi_health.core.grading_engine import GradingEngine
from cdi_health.core.report_generator import ReportGenerator
from cdi_health.utils.logging import setup_logging

def check_root() -> None:
    """Check if the script is running with root privileges."""
    if os.geteuid() != 0:
        print(
            "Error: This tool requires root privileges to access storage devices.\n"
            "Please run with sudo:\n"
            "  sudo cdi_health scan",
            file=sys.stderr,
        )
        sys.exit(1)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CDI Health - Storage Device Grading Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error output",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan and grade connected storage devices",
    )
    scan_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("reports"),
        help="Output directory for reports (default: reports/)",
    )
    scan_parser.add_argument(
        "--format",
        "-f",
        choices=["csv", "json", "text"],
        default="csv",
        help="Output format (default: csv)",
    )
    scan_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Include detailed device information in report",
    )

    # Version command
    subparsers.add_parser(
        "version",
        help="Show version information",
    )

    return parser.parse_args()

def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(debug=args.debug, quiet=args.quiet)
    logger = logging.getLogger(__name__)

    try:
        if args.command == "scan":
            # Initialize components
            device_manager = DeviceManager()
            grading_engine = GradingEngine()
            report_generator = ReportGenerator()

            # Scan devices
            logger.info("Scanning for storage devices...")
            devices = device_manager.scan_devices()

            if not devices:
                logger.error("No storage devices found")
                return 1

            # Grade devices
            logger.info("Grading devices...")
            graded_devices = grading_engine.grade_devices(devices)

            # Generate report
            logger.info("Generating report...")
            report_generator.generate_report(
                graded_devices,
                output_dir=args.output,
                format=args.format,
                detailed=args.detailed,
            )

            logger.info(f"Report generated in {args.output}")
            return 0

        elif args.command == "version":
            from cdi_health import __version__
            print(f"CDI Health v{__version__}")
            return 0

        else:
            logger.error("No command specified")
            return 1

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.debug:
            logger.exception("Detailed error:")
        return 1

if __name__ == "__main__":
    sys.exit(main())
