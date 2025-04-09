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
        """Collect data from a SATA or SAS device using JSON output."""
        try:
            # Get device info and SMART data in JSON format
            result = subprocess.run(
                ["smartctl", "-i", "-A", "-j", str(path)], # Combine -i and -A with -j
                capture_output=True,
                text=True,
                check=True,
                timeout=30 # Add a timeout
            )
            smart_data = json.loads(result.stdout)

            # Extract basic info from JSON
            vendor = smart_data.get("model_family", smart_data.get("vendor", "Unknown"))
            model = smart_data.get("model_name", "Unknown")
            serial = smart_data.get("serial_number", "Unknown")
            firmware = smart_data.get("firmware_version", "Unknown")
            capacity_bytes = smart_data.get("user_capacity", {}).get("bytes", 0)

            # SAS specific data might be within the main JSON or require separate commands (TBD)
            sas_data = smart_data.get("sas_specific_data", None) # Placeholder key

            return StorageDevice(
                path=path,
                protocol=protocol,
                vendor=vendor,
                model=model,
                serial=serial,
                firmware=firmware,
                capacity_bytes=capacity_bytes,
                smart_data=smart_data, # Store the full JSON dict
                sas_data=sas_data,
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"smartctl command failed for {path}: {e}")
            return None
        except subprocess.TimeoutExpired:
            logger.warning(f"smartctl command timed out for {path}")
            return None
        except json.JSONDecodeError as e:
             logger.warning(f"Failed to parse smartctl JSON for {path}: {e}")
             return None
        except Exception as e:
            logger.error(f"Unexpected error collecting data from {path}: {e}", exc_info=True)
            return None

    def _collect_sas_data(self, path: Path) -> dict:
        """Collect SAS-specific data (Placeholder - currently relies on smartctl JSON)."""
        # If smartctl -j includes enough SAS data, this might not be needed.
        # Otherwise, run SAS-specific commands here (e.g., sg_logs)
        logger.debug(f"SAS specific data collection for {path} not fully implemented.")
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
                        ["smartctl", "-x", "-j", str(path)],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    smart_data = json.loads(result.stdout)

                    devices.append(StorageDevice(
                        path=path,
                        protocol=TransportProtocol.NVME,
                        vendor=smart_data.get("model_family", smart_data.get("vendor", "Unknown")),
                        model=smart_data.get("model_name", "Unknown"),
                        serial=smart_data.get("serial_number", "Unknown"),
                        firmware=smart_data.get("firmware_version", "Unknown"),
                        capacity_bytes=int(smart_data.get("user_capacity", {}).get("bytes", 0)),
                        smart_data=smart_data,
                        nvme_data=smart_data  # Use full smartctl JSON output for nvme_data
                    ))
                except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse NVMe device {device.get('DevicePath', 'unknown')}: {e}")
                    continue

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse NVMe list output: {e}")

        return devices