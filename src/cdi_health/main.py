#
# Copyright (c) 2024 Circular Drive Initiative.
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
"""
Circular Drive Initiative
@language Python 3.12
@version 0.0.1
"""

# TODO: manage via isort
from __future__ import annotations

# Modules
import argparse
import csv
import html
import json
import os

# XML
from xml.etree.ElementTree import Element, SubElement, ElementTree

# Classes
from cdi_health.classes.devices import Devices


# Functions
def create_logs(devices, output_types, log_for_each):
    """
    Create Logs
    """

    # Create Logs Directory
    os.makedirs('logs', exist_ok=True)

    if log_for_each:
        for device in devices:
            device_logs(device, output_types)
    else:
        all_devices_logs(devices, output_types)


def device_logs(device, output_types):
    """
    Create logs for a single device
    """

    # CSV
    if 'csv' in output_types:
        # Open CSV File
        with open(f'logs/{device["model_number"]}-{device["serial_number"]}.csv', 'w', newline='') as csvfile:
            # Write CSV File
            writer = csv.writer(csvfile)

            # Add Keys
            writer.writerow(device.keys())

            # Add Values
            writer.writerow(device.values())

    # JSON
    if 'json' in output_types:
        # Open JSON File
        with open(f'logs/{device["model_number"]}-{device["serial_number"]}.json', 'w') as jsonfile:
            # Write JSON
            json.dump(device, jsonfile, indent=4)

    # HTML
    if 'html' in output_types:
        # Open HTML File
        with open(f'logs/{device["model_number"]}-{device["serial_number"]}.html', 'w') as htmlfile:
            # Write HTML
            htmlfile.write("<html><body><table border='1'>")

            # Loop Items
            for key, value in device.items():
                # Write HTML Item
                htmlfile.write(f"<tr><th>{html.escape(key)}</th><td>{html.escape(str(value))}</td></tr>")

            # End HTML
            htmlfile.write("</table></body></html>")

    # TXT
    if 'text' in output_types:
        # Open TXT File
        with open(f'logs/{device["model_number"]}-{device["serial_number"]}.txt', 'w') as txtfile:
            # Loop Items
            for key, value in device.items():
                # Write Item
                txtfile.write(f"{key}: {value}\n")

    # XML
    if 'xml' in output_types:
        # Create XML
        root = Element('Device')

        # Loop Items
        for key, value in device.items():
            # Create Child Element
            child = SubElement(root, key)

            # Add Text
            child.text = str(value)

        # Create XML Tree
        tree = ElementTree(root)

        # Write XML Tree
        tree.write(f'logs/{device["model_number"]}-{device["serial_number"]}.xml')


def all_devices_logs(devices, output_types):
    """
    Create logs for all devices combined
    """

    # CSV
    if 'csv' in output_types:
        # Open CSV File
        with open('logs/all_devices.csv', 'w', newline='') as csvfile:
            # Write CSV File
            writer = csv.writer(csvfile)

            # Add Keys
            writer.writerow(devices[0].keys())

            # Loop Devices
            for device in devices:
                # Add Values
                writer.writerow(device.values())

    # JSON
    if 'json' in output_types:
        # Open JSON File
        with open('logs/all_devices.json', 'w') as jsonfile:
            # Write JSON
            json.dump(devices, jsonfile, indent=4)

    # HTML
    if 'html' in output_types:
        # Open HTML File
        with open('logs/all_devices.html', 'w') as htmlfile:
            # Write HTML
            htmlfile.write("<html><body><table border='1'>")

            # Add Table Headers
            htmlfile.write("<tr>")
            for key in devices[0].keys():
                htmlfile.write(f"<th>{html.escape(key)}</th>")
            htmlfile.write("</tr>")

            # Loop Devices
            for device in devices:
                # Write HTML Items
                htmlfile.write("<tr>")
                for value in device.values():
                    htmlfile.write(f"<td>{html.escape(str(value))}</td>")
                htmlfile.write("</tr>")

            # End HTML
            htmlfile.write("</table></body></html>")

    # TXT
    if 'text' in output_types:
        # Open TXT File
        with open('logs/all_devices.txt', 'w') as txtfile:
            # Loop Devices
            for device in devices:
                # Loop Items
                for key, value in device.items():
                    # Write Item
                    txtfile.write(f"{key}: {value}\n")
                # Add a newline between devices
                txtfile.write("\n")

    # XML
    if 'xml' in output_types:
        # Create XML
        root = Element('Devices')

        # Loop Devices
        for device in devices:
            # Create Device Element
            device_elem = SubElement(root, 'Device')

            # Loop Items
            for key, value in device.items():
                # Create Child Element
                child = SubElement(device_elem, key)

                # Add Text
                child.text = str(value)

        # Create XML Tree
        tree = ElementTree(root)

        # Write XML Tree
        tree.write('logs/all_devices.xml')


# Main Function
def main():
    # Set Argument Parser
    parser = argparse.ArgumentParser(description="CDI Grading Tool")
    parser.add_argument('--verbose', action='store_true', help='Launch in Verbose Mode')
    parser.add_argument('--ignore-ata', action='store_true', help='Ignore ATA devices when scanning for Devices')
    parser.add_argument('--ignore-nvme', action='store_true', help='Ignore NVMe devices when scanning for Devices')
    parser.add_argument('--ignore-scsi', action='store_true', help='Ignore SCSI devices when scanning for Devices')
    parser.add_argument('--ignore-removable', action='store_true', help='Ignore USB/SD/MSD/MMC/eMMC devices when scanning for Devices')
    parser.add_argument('--log-for-each', action='store_true', help='Generate a log for each Device found')
    parser.add_argument('--csv', action='store_true', help="Output the Data as CSV")
    parser.add_argument('--html', action='store_true', help="Output the Data as HTML")
    parser.add_argument('--json', action='store_true', help="Output the Data as JSON")
    parser.add_argument('--text', action='store_true', help="Output the Data as TXT")
    parser.add_argument('--xml', action='store_true', help="Output the Data as XML")

    # Parse Arguments
    args = parser.parse_args()

    # Scan Devices
    d = Devices(
        ignore_ata=args.ignore_ata,
        ignore_nvme=args.ignore_nvme,
        ignore_scsi=args.ignore_scsi,
        ignore_removable=args.ignore_removable,
    )

    # Convert Device to JSON String
    devices_json = json.dumps(d.devices, indent=4)

    # Create List
    output_types = []

    # CSV
    if args.csv:
        output_types.append('csv')

    # HTML
    if args.html:
        output_types.append('html')

    # JSON
    if args.json:
        output_types.append('json')

    # Text
    if args.text:
        output_types.append('text')

    # XML
    if args.xml:
        output_types.append('xml')

    # Create Logs
    create_logs(d.devices, output_types, args.log_for_each)

    # Print
    print("Logs successfully generated.")
