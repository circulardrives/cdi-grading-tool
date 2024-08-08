"""
Circular Drive Initiative
@language Python 3.12
@version 0.0.1
"""

# Modules
import argparse
import csv
import html
import json
import os

# XML
from xml.etree.ElementTree import Element, SubElement, ElementTree

# Classes
from classes.devices import Devices


# Functions
def create_logs(device, output_types):
    """
    Create Logs
    """

    # Create Logs Directory
    os.makedirs('logs', exist_ok=True)

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


# Main Function
if __name__ == '__main__':
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
    devices = Devices(
        ignore_ata=args.ignore_ata,
        ignore_nvme=args.ignore_nvme,
        ignore_scsi=args.ignore_scsi,
        ignore_removable=args.ignore_removable,
    )

    # Convert Device to JSON String
    devices_json = json.dumps(devices.devices, indent=4)

    # Print
    print(devices_json)

    # Determine output types based on arguments
    output_types = []
    if args.csv:
        output_types.append('csv')
    if args.html:
        output_types.append('html')
    if args.json:
        output_types.append('json')
    if args.text:
        output_types.append('text')
    if args.xml:
        output_types.append('xml')

    # Create a Log for each Drive
    for device in devices.devices:
        # Create Logs
        create_logs(device, output_types)