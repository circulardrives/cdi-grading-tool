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
                    nvme_data = {}

                    # First try with smartctl basic info
                    try:
                        result = subprocess.run(
                            ["smartctl", "-i", "-j", str(path)],
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        smart_data = json.loads(result.stdout)
                    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
                        logger.warning(f"Failed to get basic smartctl info for {path}: {e}")
                        smart_data = {}

                    # Get NVMe log pages directly using nvme cli
                    try:
                        # Get SMART / Health Information (Log Identifier 02h)
                        smart_log = subprocess.run(
                            ["nvme", "smart-log", "-o", "json", str(path)],
                            capture_output=True,
                            text=True,
                        )

                        if smart_log.returncode == 0 and smart_log.stdout.strip():
                            health_data = json.loads(smart_log.stdout)
                            logger.debug(f"NVMe health data: {health_data}")
                            nvme_data["nvme_smart_health_information_log"] = health_data
                        else:
                            logger.warning(f"nvme smart-log failed: {smart_log.stderr}")

                            # Try alternative method - smartctl nvme
                            logger.debug(f"Trying smartctl for NVMe health data")
                            alt_smart = subprocess.run(
                                ["smartctl", "--xall", "--json", str(path)],
                                capture_output=True,
                                text=True,
                            )

                            if alt_smart.returncode == 0:
                                alt_data = json.loads(alt_smart.stdout)
                                if "nvme_smart_health_information_log" in alt_data:
                                    logger.debug("Found nvme_smart_health_information_log in smartctl output")
                                    nvme_data["nvme_smart_health_information_log"] = alt_data["nvme_smart_health_information_log"]
                                else:
                                    logger.warning("smartctl doesn't contain nvme_smart_health_information_log")
                            else:
                                logger.warning(f"smartctl also failed: {alt_smart.stderr}")

                                # Try a third method - use sg_logs if available
                                if shutil.which("sg_logs"):
                                    logger.debug("Trying sg_logs as last resort")
                                    sg_logs = subprocess.run(
                                        ["sg_logs", "--page=0x02", "--format=json", str(path)],
                                        capture_output=True,
                                        text=True,
                                    )
                                    if sg_logs.returncode == 0:
                                        nvme_data["nvme_smart_health_information_log"] = json.loads(sg_logs.stdout)
                                    else:
                                        logger.warning(f"sg_logs also failed: {sg_logs.stderr}")

                        # Try to construct a basic health log if we still don't have one
                        if "nvme_smart_health_information_log" not in nvme_data or not nvme_data["nvme_smart_health_information_log"]:
                            logger.debug("Constructing basic health log from available data")
                            # Create a minimal health log with at least empty fields
                            nvme_data["nvme_smart_health_information_log"] = {
                                "critical_warning": 0,
                                "temperature": 0,
                                "available_spare": 100,
                                "available_spare_threshold": 10,
                                "percentage_used": 0,
                                "data_units_read": 0,
                                "data_units_written": 0,
                                "host_reads": 0,
                                "host_writes": 0,
                                "media_errors": 0,
                                "num_err_log_entries": 0,
                            }

                        # Get Error Information (Log Identifier 01h)
                        try:
                            error_log = subprocess.run(
                                ["nvme", "error-log", "-o", "json", str(path)],
                                capture_output=True,
                                text=True,
                            )
                            if error_log.returncode == 0:
                                nvme_data["error_log"] = json.loads(error_log.stdout)
                        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
                            logger.debug(f"Error log not available: {e}")

                        # Get Firmware Slot Information (Log Identifier 03h)
                        try:
                            fw_log = subprocess.run(
                                ["nvme", "fw-log", "-o", "json", str(path)],
                                capture_output=True,
                                text=True,
                            )
                            if fw_log.returncode == 0:
                                nvme_data["firmware_log"] = json.loads(fw_log.stdout)
                        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
                            logger.debug(f"Firmware log not available: {e}")

                        # Get Self-test Log (Log Identifier 06h) if available
                        try:
                            self_test_log = subprocess.run(
                                ["nvme", "self-test-log", "-o", "json", str(path)],
                                capture_output=True,
                                text=True,
                            )
                            if self_test_log.returncode == 0:
                                nvme_data["self_test_log"] = json.loads(self_test_log.stdout)
                        except (subprocess.SubprocessError, json.JSONDecodeError) as e:
                            logger.debug(f"Self-test log not available: {e}")

                    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
                        logger.warning(f"Failed to get NVMe log pages for {path}: {e}")

                    # Get basic info from nvme id-ctrl command if smartctl failed
                    if not smart_data:
                        try:
                            id_ctrl = subprocess.run(
                                ["nvme", "id-ctrl", "-o", "json", str(path)],
                                capture_output=True,
                                text=True,
                                check=True,
                            )
                            ctrl_data = json.loads(id_ctrl.stdout)

                            # Extract vendor, model, serial, firmware from nvme id-ctrl
                            vendor = ctrl_data.get("vid", "Unknown")
                            model = ctrl_data.get("mn", "Unknown").strip()
                            serial = ctrl_data.get("sn", "Unknown").strip()
                            firmware = ctrl_data.get("fr", "Unknown").strip()

                            # Get capacity from nvme id-ns command
                            id_ns = subprocess.run(
                                ["nvme", "id-ns", "-o", "json", str(path)],
                                capture_output=True,
                                text=True,
                                check=True,
                            )
                            ns_data = json.loads(id_ns.stdout)
                            # Calculate capacity in bytes
                            lba_size = int(ns_data.get("lbaf", [{"ds": 9}])[0].get("ds", 9))
                            lba_count = int(ns_data.get("nsze", 0))
                            capacity_bytes = lba_count * (2 ** lba_size)
                        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
                            logger.warning(f"Failed to get NVMe identity data for {path}: {e}")
                            # Use defaults if we can't get real data
                            vendor = "Unknown"
                            model = "Unknown"
                            serial = "Unknown"
                            firmware = "Unknown"
                            capacity_bytes = 0
                    else:
                        # Extract from smartctl data
                        vendor = smart_data.get("model_family", smart_data.get("vendor", "Unknown"))
                        model = smart_data.get("model_name", "Unknown")
                        serial = smart_data.get("serial_number", "Unknown")
                        firmware = smart_data.get("firmware_version", "Unknown")
                        capacity_bytes = int(smart_data.get("user_capacity", {}).get("bytes", 0))

                    # Merge all data
                    if smart_data:
                        nvme_data["smartctl"] = smart_data

                    devices.append(StorageDevice(
                        path=path,
                        protocol=TransportProtocol.NVME,
                        vendor=vendor,
                        model=model,
                        serial=serial,
                        firmware=firmware,
                        capacity_bytes=capacity_bytes,
                        smart_data=smart_data if smart_data else {},
                        nvme_data=nvme_data
                    ))

                except Exception as e:
                    logger.warning(f"Failed to parse NVMe device {device.get('DevicePath', 'unknown')}: {e}")
                    continue

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse NVMe list output: {e}")

        return devices