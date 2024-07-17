"""
Circular Drive Initiative
@language Python 3.12
@version 0.0.1
"""

# Modules
import argparse
import json

# Classes
from classes.devices import Devices

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
    parser.add_argument('--json', action='store_true', help="Output the Data as JSON string")

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
