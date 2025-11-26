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
Circular Drive Initiative - Example Usage

# Export All Devices as JSON - Single File
sudo python3 example.py --json

# Export All Devices as JSON - File for each Disk
sudo python3 example.py --log-for-each --json
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


def main():
    """
    Main
    """

    # Check Prerequisites
    check_prerequisites()

    # Set Argument Parser
    parser = argparse.ArgumentParser(description="CDI Grading Tool")

    # Device Filtering Arguments
    parser.add_argument("--ignore-ata", action="store_true", help="Ignore ATA devices when scanning")
    parser.add_argument("--ignore-nvme", action="store_true", help="Ignore NVMe devices when scanning")
    parser.add_argument("--ignore-scsi", action="store_true", help="Ignore SCSI devices when scanning")
    parser.add_argument(
        "--ignore-removable", action="store_true", help="Ignore USB/SD/MSD/MMC/eMMC devices when scanning"
    )

    # Output Format Arguments
    output_formats = ["csv", "html", "json", "text", "xml"]

    # Loop Formats
    for fmt in output_formats:
        # Add Arguments
        parser.add_argument(f"--{fmt}", action="store_true", help=f"Output the Data as {fmt.upper()}")

    # Logging Argument
    parser.add_argument("--log-for-each", action="store_true", help="Generate a log for each device found")

    # Verbose Mode
    parser.add_argument("--verbose", action="store_true", help="Launch in Verbose Mode")

    # No Args
    if len(sys.argv) == 1:
        # Print Help
        parser.print_help()

        # Exit
        sys.exit(0)

    # Parse Arguments
    args = parser.parse_args()

    # Scan Devices
    device_scanner = Devices(
        ignore_ata=args.ignore_ata,
        ignore_nvme=args.ignore_nvme,
        ignore_scsi=args.ignore_scsi,
    )

    # Get Devices as JSON
    devices_json = json.dumps(device_scanner.devices, indent=4)

    # Verbose
    if args.verbose:
        # Print
        print("Scanned Devices:", devices_json)

    # Get Output Formats
    selected_outputs = {fmt for fmt in output_formats if getattr(args, fmt)}

    # Create Logs
    create_logs(device_scanner.devices, selected_outputs, args.log_for_each)


if __name__ == "__main__":
    # Run
    main()
