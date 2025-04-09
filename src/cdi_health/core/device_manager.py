"""
Device Manager

This module handles device detection and data collection for storage devices.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class TransportProtocol(Enum):
    """Storage device transport protocols."""
    SATA = "sata"
    SAS = "sas"
    NVME = "nvme"
    UNKNOWN = "unknown"

@dataclass
class StorageDevice:
    """Storage device information."""
    path: Path
    protocol: TransportProtocol
    vendor: str
    model: str
    serial: str
    firmware: str
    capacity_bytes: int
    smart_data: dict
    nvme_data: Optional[dict] = None
    sas_data: Optional[dict] = None

class DeviceManager:
    """Manages storage device detection and data collection."""

    REQUIRED_TOOLS = {
        "nvme": "nvme-cli",
        "smartctl": "smartmontools",
        "sg_map26": "sg3-utils",
        "sg_turs": "sg3-utils",
    }

    def __init__(self):
        """Initialize the device manager."""
        self._check_prerequisites()
        self._check_root()

    def _check_prerequisites(self) -> None:
        """Check if required tools are installed."""
        missing_tools = []
        for tool, package in self.REQUIRED_TOOLS.items():
            if not shutil.which(tool):
                missing_tools.append(f"{tool} (from {package})")

        if missing_tools:
            raise RuntimeError(
                f"Missing required tools: {', '.join(missing_tools)}. "
                "Please install them before running this tool."
            )

    def _check_root(self) -> None:
        """Check if running with root privileges."""
        if os.geteuid() != 0:
            raise RuntimeError(
                "This tool requires root privileges to access storage devices. "
                "Please run with sudo or as root."
            )

    def scan_devices(self) -> List[StorageDevice]:
        """Scan for and collect data from storage devices."""
        devices = []

        # Scan SATA/SAS devices using smartctl
        try:
            result = subprocess.run(
                ["smartctl", "--scan"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                path = Path(line.split()[0])
                protocol = self._detect_protocol(path)
                if protocol in (TransportProtocol.SATA, TransportProtocol.SAS):
                    device = self._collect_sata_sas_data(path, protocol)
                    if device:
                        devices.append(device)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Error scanning SATA/SAS devices: {e}")

        # Scan NVMe devices
        try:
            result = subprocess.run(
                ["nvme", "list", "-o", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            nvme_devices = self._parse_nvme_list(result.stdout)
            for device in nvme_devices:
                devices.append(device)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Error scanning NVMe devices: {e}")

        return devices

    def _detect_protocol(self, path: Path) -> TransportProtocol:
        """Detect the transport protocol of a device."""
        try:
            result = subprocess.run(
                ["smartctl", "-i", str(path)],
                capture_output=True,
                text=True,
                check=True,
            )
            if "SATA" in result.stdout:
                return TransportProtocol.SATA
            elif "SAS" in result.stdout:
                return TransportProtocol.SAS
            elif "NVMe" in result.stdout:
                return TransportProtocol.NVME
        except subprocess.CalledProcessError:
            pass
        return TransportProtocol.UNKNOWN

    def _collect_sata_sas_data(self, path: Path, protocol: TransportProtocol) -> Optional[StorageDevice]:
        """Collect data from a SATA or SAS device."""
        try:
            # Get basic info
            result = subprocess.run(
                ["smartctl", "-i", str(path)],
                capture_output=True,
                text=True,
                check=True,
            )
            info = self._parse_smartctl_info(result.stdout)

            # Get SMART data
            result = subprocess.run(
                ["smartctl", "-A", str(path)],
                capture_output=True,
                text=True,
                check=True,
            )
            smart_data = self._parse_smartctl_attributes(result.stdout)

            # Get SAS specific data if needed
            sas_data = None
            if protocol == TransportProtocol.SAS:
                sas_data = self._collect_sas_data(path)

            return StorageDevice(
                path=path,
                protocol=protocol,
                vendor=info["vendor"],
                model=info["model"],
                serial=info["serial"],
                firmware=info["firmware"],
                capacity_bytes=info["capacity_bytes"],
                smart_data=smart_data,
                sas_data=sas_data,
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"Error collecting data from {path}: {e}")
            return None

    def _collect_sas_data(self, path: Path) -> dict:
        """Collect SAS-specific data."""
        # TODO: Implement SAS-specific data collection
        return {}

    def _parse_nvme_list(self, output: str) -> List[StorageDevice]:
        """Parse NVMe device list output."""
        devices = []

        try:
            data = json.loads(output)
            for device in data.get("Devices", []):
                try:
                    path = Path(device["DevicePath"])
                    result = subprocess.run(
                        ["smartctl", "-i", "-j", str(path)],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    smart_data = json.loads(result.stdout)

                    devices.append(StorageDevice(
                        path=path,
                        protocol=TransportProtocol.NVME,
                        vendor=smart_data.get("model_family", "Unknown"),
                        model=smart_data.get("model_name", "Unknown"),
                        serial=smart_data.get("serial_number", "Unknown"),
                        firmware=smart_data.get("firmware_version", "Unknown"),
                        capacity_bytes=int(smart_data.get("user_capacity", {}).get("bytes", 0)),
                        smart_data=smart_data,
                        nvme_data=smart_data.get("nvme", {})
                    ))
                except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse NVMe device {device.get('DevicePath', 'unknown')}: {e}")
                    continue

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse NVMe list output: {e}")

        return devices

    def _parse_smartctl_info(self, output: str) -> dict:
        """Parse smartctl info output."""
        info = {
            "vendor": "Unknown",
            "model": "Unknown",
            "serial": "Unknown",
            "firmware": "Unknown",
            "capacity_bytes": 0
        }

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            if "Vendor:" in line:
                info["vendor"] = line.split("Vendor:", 1)[1].strip()
            elif "Product:" in line:
                info["model"] = line.split("Product:", 1)[1].strip()
            elif "Serial Number:" in line:
                info["serial"] = line.split("Serial Number:", 1)[1].strip()
            elif "Firmware Version:" in line:
                info["firmware"] = line.split("Firmware Version:", 1)[1].strip()
            elif "User Capacity:" in line:
                # Extract bytes from line like: "User Capacity:    500,107,862,016 bytes [500 GB]"
                try:
                    capacity_str = line.split("[")[0].split("bytes")[0].strip().replace(",", "")
                    info["capacity_bytes"] = int(capacity_str)
                except (ValueError, IndexError):
                    pass

        return info

    def _parse_smartctl_attributes(self, output: str) -> dict:
        """Parse smartctl attributes output."""
        attributes = {}

        # Find the start of the attributes table
        lines = output.splitlines()
        start_idx = -1
        for i, line in enumerate(lines):
            if "ID#" in line and "ATTRIBUTE_NAME" in line:
                start_idx = i + 1
                break

        if start_idx == -1:
            return attributes

        # Parse the attributes table
        for line in lines[start_idx:]:
            if not line.strip():
                continue

            try:
                # Split the line into columns
                parts = line.split()
                if len(parts) >= 10:
                    id_num = parts[0]
                    name = " ".join(parts[1:-8])
                    value = parts[-8]
                    worst = parts[-7]
                    threshold = parts[-6]
                    raw_value = " ".join(parts[-5:])

                    attributes[name] = {
                        "id": id_num,
                        "value": value,
                        "worst": worst,
                        "threshold": threshold,
                        "raw_value": raw_value
                    }
            except (ValueError, IndexError):
                continue

        return attributes