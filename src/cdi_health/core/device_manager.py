"""
Device Manager

This module handles device detection and data collection for storage devices.
"""

from __future__ import annotations

import logging
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
        # TODO: Implement NVMe device list parsing
        return []

    def _parse_smartctl_info(self, output: str) -> dict:
        """Parse smartctl info output."""
        # TODO: Implement smartctl info parsing
        return {}

    def _parse_smartctl_attributes(self, output: str) -> dict:
        """Parse smartctl attributes output."""
        # TODO: Implement smartctl attributes parsing
        return {}