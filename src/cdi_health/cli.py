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

"""
CDI Health CLI - Command Line Interface

Main entry point for the CDI Health Scanner tool.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime

from cdi_health.classes.colors import Colors
from cdi_health.classes.formatter import get_formatter


# Version
__version__ = "1.0.0"


# Required tools for real device scanning
REQUIRED_TOOLS = [
    "nvme",
    "smartctl",
    "openSeaChest_Basics",
    "openSeaChest_SMART",
    "sg_map26",
    "sg_turs",
]


def check_prerequisites() -> list[str]:
    """Check for required tools and return list of missing ones."""
    missing = []
    for tool in REQUIRED_TOOLS:
        if not shutil.which(tool):
            missing.append(tool)
    return missing


def scan_devices_real(ignore_ata=False, ignore_nvme=False, ignore_scsi=False) -> list[dict]:
    """Scan real devices."""
    from cdi_health.classes.devices import Devices

    devices = Devices(
        ignore_ata=ignore_ata,
        ignore_nvme=ignore_nvme,
        ignore_scsi=ignore_scsi,
    )
    return devices.devices


def scan_devices_mock(mock_path: str, ignore_ata=False, ignore_nvme=False, ignore_scsi=False) -> list[dict]:
    """Scan mock devices from directory."""
    from cdi_health.classes.mock import MockDevices

    devices = MockDevices(
        mock_data_path=mock_path,
        ignore_ata=ignore_ata,
        ignore_nvme=ignore_nvme,
        ignore_scsi=ignore_scsi,
    )
    return devices.devices


def scan_single_mock(mock_file: str) -> list[dict]:
    """Scan single mock device from file."""
    from cdi_health.classes.mock import create_mock_device

    device = create_mock_device(json_file=mock_file)
    return [device.to_dict(pop=True)]


def cmd_scan(args) -> int:
    """Execute scan command."""
    # Auto-detect color support unless explicitly set
    if args.no_color:
        Colors.disable()
    else:
        Colors.auto_detect()

    # Determine if using mock mode
    mock_mode = args.mock_data is not None or args.mock_file is not None

    # Check prerequisites for real device scanning
    if not mock_mode:
        missing = check_prerequisites()
        if missing:
            print("Error: Required tools not found:", file=sys.stderr)
            for tool in missing:
                print(f"  - {tool}", file=sys.stderr)
            print("\nPlease install them before scanning real devices.", file=sys.stderr)
            return 1

    # Load custom configuration if provided
    if args.config:
        from cdi_health.classes.config import configure_thresholds

        configure_thresholds(args.config)
        if args.verbose:
            print(f"Loaded configuration from: {args.config}")

    # Scan devices
    try:
        if args.mock_file:
            devices = scan_single_mock(args.mock_file)
            if args.verbose:
                print(f"Loaded mock device from: {args.mock_file}")
        elif args.mock_data:
            devices = scan_devices_mock(
                args.mock_data,
                ignore_ata=args.ignore_ata,
                ignore_nvme=args.ignore_nvme,
                ignore_scsi=args.ignore_scsi,
            )
            if args.verbose:
                print(f"Loaded {len(devices)} mock devices from: {args.mock_data}")
        else:
            devices = scan_devices_real(
                ignore_ata=args.ignore_ata,
                ignore_nvme=args.ignore_nvme,
                ignore_scsi=args.ignore_scsi,
            )
            if args.verbose:
                print(f"Scanned {len(devices)} devices")
    except Exception as e:
        print(f"Error scanning devices: {e}", file=sys.stderr)
        return 1

    if not devices:
        print("No devices found.")
        return 0

    # Format output
    try:
        formatter = get_formatter(args.output)
        output = formatter.format(devices)
        print(output)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_report(args) -> int:
    """Execute report command."""
    # Determine if using mock mode
    mock_mode = args.mock_data is not None or args.mock_file is not None

    # Check prerequisites for real device scanning
    if not mock_mode:
        missing = check_prerequisites()
        if missing:
            print("Error: Required tools not found:", file=sys.stderr)
            for tool in missing:
                print(f"  - {tool}", file=sys.stderr)
            return 1

    # Load custom configuration if provided
    if args.config:
        from cdi_health.classes.config import configure_thresholds

        configure_thresholds(args.config)

    # Scan devices
    try:
        if args.mock_file:
            devices = scan_single_mock(args.mock_file)
        elif args.mock_data:
            devices = scan_devices_mock(
                args.mock_data,
                ignore_ata=args.ignore_ata,
                ignore_nvme=args.ignore_nvme,
                ignore_scsi=args.ignore_scsi,
            )
        else:
            devices = scan_devices_real(
                ignore_ata=args.ignore_ata,
                ignore_nvme=args.ignore_nvme,
                ignore_scsi=args.ignore_scsi,
            )
    except Exception as e:
        print(f"Error scanning devices: {e}", file=sys.stderr)
        return 1

    if not devices:
        print("No devices found.")
        return 0

    # Generate report
    from cdi_health.classes.reporter import ReportGenerator

    reporter = ReportGenerator()

    # Determine output file
    if args.output_file:
        output_path = args.output_file
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        ext = "html" if args.format == "html" else "pdf"
        output_path = f"cdi-report-{timestamp}.{ext}"

    try:
        if args.format == "html":
            reporter.generate_html(devices, output_path)
        else:
            reporter.generate_pdf(devices, output_path)

        print(f"Report generated: {output_path}")
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_watch(args) -> int:
    """Execute watch command."""
    from cdi_health.classes.watch import WatchMode

    # Determine if using mock mode
    mock_mode = args.mock_data is not None or args.mock_file is not None
    mock_path = args.mock_data or args.mock_file

    # Check prerequisites for real device scanning
    if not mock_mode:
        missing = check_prerequisites()
        if missing:
            print("Error: Required tools not found:", file=sys.stderr)
            for tool in missing:
                print(f"  - {tool}", file=sys.stderr)
            return 1

    # Load custom configuration if provided
    if args.config:
        from cdi_health.classes.config import configure_thresholds

        configure_thresholds(args.config)

    watch = WatchMode(
        interval=args.interval,
        mock_mode=mock_mode,
        mock_data_path=mock_path,
    )

    watch.start()
    return 0


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a parser."""
    # Global options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed information",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        help="Path to YAML config file for custom thresholds",
    )

    # Mock mode options
    parser.add_argument(
        "--mock-data",
        metavar="PATH",
        help="Use mock data directory instead of real devices",
    )
    parser.add_argument(
        "--mock-file",
        metavar="FILE",
        help="Use specific mock JSON file for single device",
    )

    # Device filtering
    parser.add_argument(
        "--ignore-ata",
        action="store_true",
        help="Ignore ATA devices",
    )
    parser.add_argument(
        "--ignore-nvme",
        action="store_true",
        help="Ignore NVMe devices",
    )
    parser.add_argument(
        "--ignore-scsi",
        action="store_true",
        help="Ignore SCSI devices",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="cdi-health",
        description="CDI Health Scanner - Storage Device Health Assessment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all devices (default: table output)
  cdi-health scan

  # Scan with JSON output
  cdi-health scan -o json

  # Test with mock data
  cdi-health scan --mock-data src/cdi_health/mock_data

  # Generate HTML report
  cdi-health report --format html --mock-data src/cdi_health/mock_data

  # Continuous monitoring
  cdi-health watch --interval 30
""",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan and display drive health (default)",
        description="Scan storage devices and display health information.",
    )
    add_common_arguments(scan_parser)
    scan_parser.add_argument(
        "-o", "--output",
        choices=["table", "json", "csv", "yaml"],
        default="table",
        help="Output format (default: table)",
    )
    scan_parser.add_argument(
        "--all",
        action="store_true",
        help="Show all device attributes (not just summary)",
    )
    scan_parser.add_argument(
        "--device",
        metavar="PATH",
        help="Scan specific device only",
    )

    # Report command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate detailed health report",
        description="Generate a detailed HTML or PDF health report.",
    )
    add_common_arguments(report_parser)
    report_parser.add_argument(
        "--format",
        choices=["html", "pdf"],
        default="html",
        help="Report format (default: html)",
    )
    report_parser.add_argument(
        "--output-file",
        metavar="PATH",
        help="Output file path (default: cdi-report-{timestamp}.html)",
    )

    # Watch command
    watch_parser = subparsers.add_parser(
        "watch",
        help="Continuous monitoring mode",
        description="Continuously monitor device health and report changes.",
    )
    add_common_arguments(watch_parser)
    watch_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="N",
        help="Seconds between scans (default: 60)",
    )

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()

    # Handle no arguments - show help or run scan
    if len(sys.argv) == 1:
        # Default to scan command with table output
        sys.argv.append("scan")

    args = parser.parse_args()

    # Copy global args to command-specific namespace if needed
    if not hasattr(args, "ignore_ata"):
        args.ignore_ata = False
    if not hasattr(args, "ignore_nvme"):
        args.ignore_nvme = False
    if not hasattr(args, "ignore_scsi"):
        args.ignore_scsi = False

    # Execute command
    if args.command == "scan" or args.command is None:
        # Default output format for scan
        if not hasattr(args, "output"):
            args.output = "table"
        return cmd_scan(args)
    elif args.command == "report":
        return cmd_report(args)
    elif args.command == "watch":
        return cmd_watch(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
