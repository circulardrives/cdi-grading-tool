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
Circular Drive Initiative - Example Usage

# Export All Devices as JSON - Single File
sudo python3 example.py --json

# Export All Devices as JSON - File for each Disk
sudo python3 example.py --log-for-each --json

# Test with mock data
python3 example.py --mock-data src/cdi_health/mock_data --json

# Test with single mock file
python3 example.py --mock-file src/cdi_health/mock_data/ata/healthy_hdd.json --json

# Validate output
sudo python3 example.py --json --validate

# Use custom thresholds
sudo python3 example.py --config custom_thresholds.yaml --json

# Watch mode
sudo python3 example.py --watch --watch-interval 30
"""

# Annotations
from __future__ import annotations

# Modules
import argparse
import csv
import html
import json
import os
import shutil
import sys

# XML
from xml.etree.ElementTree import Element, ElementTree, SubElement

# Classes
from cdi_health.classes.devices import Devices

# Required Tools
REQUIRED_TOOLS = [
    "nvme",  # NVMe CLI
    "smartctl",  # Smartmontools
    "openSeaChest_Basics",  # OpenSeaChest
    "openSeaChest_SMART",  # OpenSeaChest
    "sg_map26",  # SG3-utils
    "sg_turs",  # SG3-utils
]


def check_prerequisites():
    """
    Check Prerequisites
    """

    # Reset
    missing_tools = []

    # Loop Tools
    for tool in REQUIRED_TOOLS:
        # If Not Found
        if not shutil.which(tool):
            # Append to Missing List
            missing_tools.append(tool)

    # If Missing Tools
    if missing_tools:
        # Print
        print("\nERROR: The following required programs are missing:\n", file=sys.stderr)

        # Loop Missing Tools
        for tool in missing_tools:
            # Print
            print(f"  - {tool}", file=sys.stderr)

        # Print
        print("\nPlease install them before running this script.\n", file=sys.stderr)

        # Exit
        sys.exit(1)


def create_logs(devices, output_types, log_for_each):
    """
    Create Logs
    """

    # Create Logs Directory
    os.makedirs("./logs", exist_ok=True)

    # If Log for each Device
    if log_for_each:
        # Loop Devices
        for device in devices:
            # Create Device Logs
            device_logs(device, output_types)

    else:
        # Create All Device Logs
        all_devices_logs(devices, output_types)

    # Print
    print("Logs successfully generated.")


def device_logs(device, output_type_list):
    """
    Create logs for a single device
    """

    # CSV
    if "csv" in output_type_list:
        # Open CSV File
        with open(
            f"logs/{device['transport_protocol']}-{device['model_number']}-{device['serial_number']}.csv",
            "w",
            newline="",
        ) as csvfile:
            # Write CSV File
            writer = csv.writer(csvfile)

            # Add Keys
            writer.writerow(device.keys())

            # Add Values
            writer.writerow(device.values())

    # JSON
    if "json" in output_type_list:
        # Open JSON File
        with open(
            f"logs/{device['transport_protocol']}-{device['model_number']}-{device['serial_number']}.json", "w"
        ) as jsonfile:
            # Write JSON
            json.dump(device, jsonfile, indent=4)

    # HTML
    if "html" in output_type_list:
        # Open HTML File
        with open(
            f"logs/{device['transport_protocol']}-{device['model_number']}-{device['serial_number']}.html", "w"
        ) as htmlfile:
            # Write HTML
            htmlfile.write("<html><body><table border='1'>")

            # Loop Items
            for key, value in device.items():
                # Write HTML Item
                htmlfile.write(f"<tr><th>{html.escape(key)}</th><td>{html.escape(str(value))}</td></tr>")

            # End HTML
            htmlfile.write("</table></body></html>")

    # TXT
    if "text" in output_type_list:
        # Open TXT File
        with open(
            f"logs/{device['transport_protocol']}-{device['model_number']}-{device['serial_number']}.txt", "w"
        ) as txtfile:
            # Loop Items
            for key, value in device.items():
                # Write Item
                txtfile.write(f"{key}: {value}\n")

    # XML
    if "xml" in output_type_list:
        # Create XML
        root = Element("Device")

        # Loop Items
        for key, value in device.items():
            # Create Child Element
            child = SubElement(root, key)

            # Add Text
            child.text = str(value)

        # Create XML Tree
        tree = ElementTree(root)

        # Write XML Tree
        tree.write(f"logs/{device['transport_protocol']}-{device['model_number']}-{device['serial_number']}.xml")


def all_devices_logs(devices, output_types):
    """
    Create logs for all devices combined
    """

    # CSV
    if "csv" in output_types:
        # Open CSV File
        with open("logs/all_devices.csv", "w", newline="") as csvfile:
            # Write CSV File
            writer = csv.writer(csvfile)

            # Add Keys
            writer.writerow(devices[0].keys())

            # Loop Devices
            for device in devices:
                # Add Values
                writer.writerow(device.values())

    # JSON
    if "json" in output_types:
        # Open JSON File
        with open("logs/all_devices.json", "w") as jsonfile:
            # Write JSON
            json.dump(devices, jsonfile, indent=4)

    # HTML
    if "html" in output_types:
        # Open HTML File
        with open("all_devices.html", "w") as htmlfile:
            # Write HTML
            htmlfile.write("<html><body><table border='1'>")

            # Add Table Headers
            htmlfile.write("<tr>")
            for key in devices[0].keys():
                # Write Header
                htmlfile.write(f"<th>{html.escape(key)}</th>")

            # Write Closing Row
            htmlfile.write("</tr>")

            # Loop Devices
            for device in devices:
                # Write New Row
                htmlfile.write("<tr>")

                # Loop Items
                for value in device.values():
                    # Write Cell Item
                    htmlfile.write(f"<td>{html.escape(str(value))}</td>")

                # Write Closing Row
                htmlfile.write("</tr>")

            # End HTML
            htmlfile.write("</table></body></html>")

    # TXT
    if "text" in output_types:
        # Open TXT File
        with open("logs/all_devices.txt", "w") as txtfile:
            # Loop Devices
            for device in devices:
                # Loop Items
                for key, value in device.items():
                    # Write Item
                    txtfile.write(f"{key}: {value}\n")

                # Add New Line
                txtfile.write("\n")

    # XML
    if "xml" in output_types:
        # Create XML
        root = Element("Devices")

        # Loop Devices
        for device in devices:
            # Create Device Element
            device_elem = SubElement(root, "Device")

            # Loop Items
            for key, value in device.items():
                # Create Child Element
                child = SubElement(device_elem, key)

                # Add Text
                child.text = str(value)

        # Create XML Tree
        tree = ElementTree(root)

        # Write XML Tree
        tree.write("logs/all_devices.xml")


def scan_devices_real(ignore_ata=False, ignore_nvme=False, ignore_scsi=False):
    """
    Scan real devices using Devices class.

    :return: List of device dictionaries
    """
    device_scanner = Devices(
        ignore_ata=ignore_ata,
        ignore_nvme=ignore_nvme,
        ignore_scsi=ignore_scsi,
    )
    return device_scanner.devices


def scan_devices_mock(mock_path, ignore_ata=False, ignore_nvme=False, ignore_scsi=False):
    """
    Scan mock devices from mock data path.

    :param mock_path: Path to mock data directory or file
    :return: List of device dictionaries
    """
    from cdi_health.classes.mock import MockDevices

    mock_devices = MockDevices(
        mock_data_path=mock_path,
        ignore_ata=ignore_ata,
        ignore_nvme=ignore_nvme,
        ignore_scsi=ignore_scsi,
    )
    return mock_devices.devices


def scan_single_mock_device(mock_file):
    """
    Create a single mock device from a JSON file.

    :param mock_file: Path to mock JSON file
    :return: List containing single device dictionary
    """
    from cdi_health.classes.mock import create_mock_device

    device = create_mock_device(json_file=mock_file)
    return [device.to_dict(pop=True)]


def validate_output(devices, verbose=False):
    """
    Validate device output and print results.

    :param devices: List of device dictionaries
    :param verbose: Include info-level messages
    """
    from cdi_health.classes.validation import format_validation_report, validate_devices_output

    results = validate_devices_output(devices)
    report = format_validation_report(results, verbose=verbose)
    print(report)

    # Return non-zero exit code if validation failed
    if any(not r.is_valid for r in results):
        return 1
    return 0


def run_watch_mode(args):
    """
    Run continuous monitoring mode.

    :param args: Parsed arguments
    """
    from cdi_health.classes.watch import WatchMode

    # Determine if using mock mode
    mock_mode = args.mock_data is not None or args.mock_file is not None
    mock_path = args.mock_data or args.mock_file

    watch = WatchMode(
        interval=args.watch_interval,
        mock_mode=mock_mode,
        mock_data_path=mock_path,
    )

    watch.start()


def main():
    """
    Main
    """

    # Set Argument Parser
    parser = argparse.ArgumentParser(
        description="CDI Grading Tool - Storage Device Health Assessment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan real devices and output JSON
  sudo python3 -m cdi_health --json

  # Test with mock data
  python3 -m cdi_health --mock-data src/cdi_health/mock_data --json

  # Test with single mock file
  python3 -m cdi_health --mock-file src/cdi_health/mock_data/ata/healthy_hdd.json --json

  # Validate output schema
  sudo python3 -m cdi_health --json --validate

  # Use custom threshold configuration
  sudo python3 -m cdi_health --config custom_thresholds.yaml --json

  # Continuous monitoring mode
  sudo python3 -m cdi_health --watch --watch-interval 30
""",
    )

    # Mock Mode Arguments
    mock_group = parser.add_argument_group("Mock Mode", "Test without real hardware")
    mock_group.add_argument(
        "--mock-data",
        metavar="PATH",
        help="Use mock data directory instead of real devices",
    )
    mock_group.add_argument(
        "--mock-file",
        metavar="FILE",
        help="Use specific mock JSON file for single device",
    )

    # Configuration Arguments
    config_group = parser.add_argument_group("Configuration", "Customize thresholds and behavior")
    config_group.add_argument(
        "--config",
        metavar="FILE",
        help="Path to YAML config file for custom thresholds",
    )
    config_group.add_argument(
        "--validate",
        action="store_true",
        help="Validate output schema and report issues",
    )

    # Watch Mode Arguments
    watch_group = parser.add_argument_group("Watch Mode", "Continuous monitoring")
    watch_group.add_argument(
        "--watch",
        action="store_true",
        help="Enable continuous monitoring mode",
    )
    watch_group.add_argument(
        "--watch-interval",
        type=int,
        default=60,
        metavar="N",
        help="Seconds between scans in watch mode (default: 60)",
    )

    # Device Filtering Arguments
    filter_group = parser.add_argument_group("Device Filtering", "Filter which devices to scan")
    filter_group.add_argument("--ignore-ata", action="store_true", help="Ignore ATA devices when scanning")
    filter_group.add_argument("--ignore-nvme", action="store_true", help="Ignore NVMe devices when scanning")
    filter_group.add_argument("--ignore-scsi", action="store_true", help="Ignore SCSI devices when scanning")
    filter_group.add_argument(
        "--ignore-removable", action="store_true", help="Ignore USB/SD/MSD/MMC/eMMC devices when scanning"
    )

    # Output Format Arguments
    output_group = parser.add_argument_group("Output Formats", "Select output format(s)")
    output_formats = ["csv", "html", "json", "text", "xml"]

    # Loop Formats
    for fmt in output_formats:
        # Add Arguments
        output_group.add_argument(f"--{fmt}", action="store_true", help=f"Output the data as {fmt.upper()}")

    # Logging Argument
    output_group.add_argument("--log-for-each", action="store_true", help="Generate a log for each device found")

    # Verbose Mode
    parser.add_argument("--verbose", action="store_true", help="Launch in verbose mode")

    # No Args
    if len(sys.argv) == 1:
        # Print Help
        parser.print_help()

        # Exit
        sys.exit(0)

    # Parse Arguments
    args = parser.parse_args()

    # Determine if using mock mode
    mock_mode = args.mock_data is not None or args.mock_file is not None

    # Check Prerequisites (skip in mock mode)
    if not mock_mode:
        check_prerequisites()

    # Load custom configuration if provided
    if args.config:
        from cdi_health.classes.config import configure_thresholds

        configure_thresholds(args.config)
        if args.verbose:
            print(f"Loaded configuration from: {args.config}")

    # Handle watch mode
    if args.watch:
        run_watch_mode(args)
        sys.exit(0)

    # Scan Devices
    if args.mock_file:
        # Single mock file
        devices = scan_single_mock_device(args.mock_file)
        if args.verbose:
            print(f"Loaded mock device from: {args.mock_file}")
    elif args.mock_data:
        # Mock data directory
        devices = scan_devices_mock(
            args.mock_data,
            ignore_ata=args.ignore_ata,
            ignore_nvme=args.ignore_nvme,
            ignore_scsi=args.ignore_scsi,
        )
        if args.verbose:
            print(f"Loaded {len(devices)} mock devices from: {args.mock_data}")
    else:
        # Real devices
        devices = scan_devices_real(
            ignore_ata=args.ignore_ata,
            ignore_nvme=args.ignore_nvme,
            ignore_scsi=args.ignore_scsi,
        )
        if args.verbose:
            print(f"Scanned {len(devices)} real devices")

    # Handle validation
    if args.validate:
        exit_code = validate_output(devices, verbose=args.verbose)
        # Continue with output if validation passed
        if exit_code != 0:
            sys.exit(exit_code)

    # Get Devices as JSON for verbose output
    if args.verbose:
        devices_json = json.dumps(devices, indent=4)
        print("Devices:", devices_json)

    # Get Output Formats
    selected_outputs = {fmt for fmt in output_formats if getattr(args, fmt)}

    # If no output format selected and not validate-only, default to json stdout
    if not selected_outputs and not args.log_for_each:
        # Output JSON to stdout
        if args.json or len(selected_outputs) == 0:
            print(json.dumps(devices, indent=2))
    else:
        # Create Logs
        if devices:
            create_logs(devices, selected_outputs, args.log_for_each)
        else:
            print("No devices found.")


if __name__ == "__main__":
    # Run
    main()
