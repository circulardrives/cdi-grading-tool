"""
Report Generator

This module generates reports in various formats based on graded devices.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

from cdi_health.core.grading_engine import GradedDevice, DeviceStatus

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generates reports in various formats."""

    def generate_report(
        self,
        graded_devices: List[GradedDevice],
        output_dir: Path,
        format: str = "csv",
        detailed: bool = False,
    ) -> None:
        """Generate a report in the specified format."""
        output_dir.mkdir(parents=True, exist_ok=True)

        if format == "csv":
            self._generate_csv_report(graded_devices, output_dir, detailed)
        elif format == "json":
            self._generate_json_report(graded_devices, output_dir, detailed)
        elif format == "text":
            self._generate_text_report(graded_devices, output_dir, detailed)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_csv_report(
        self,
        graded_devices: List[GradedDevice],
        output_dir: Path,
        detailed: bool,
    ) -> None:
        """Generate a CSV report."""
        output_file = output_dir / "device_grades.csv"
        logger.info(f"Generating CSV report: {output_file}")

        # Define CSV columns based on PRD
        fieldnames = [
            "SerialNumber",
            "Model",
            "Firmware",
            "Capacity(GB)",
            "Protocol",
            "Status",
            "FailureReason/Flag",
            "POH_Readable",
            "POH_Hours",
            "ReallocatedSectors (HDD)",
            "PendingSectors (HDD)",
            "PercentUsed (SSD)",
            "AvailableSpare% (SSD)",
            "MediaErrors (NVMe)",
            "HostReads(GB)",
            "HostWrites(GB)",
            "MaxTemp",
            "AvgTemp",
            "WarningTempTime(min)",
            "CriticalTempTime(min)",
        ]

        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for graded in graded_devices:
                row = {key: "" for key in fieldnames} # Initialize row with empty strings

                device = graded.device # Get device, could be None if initial scan failed

                if device: # Basic info if device exists
                    row["SerialNumber"] = device.serial
                    row["Model"] = device.model
                    row["Firmware"] = device.firmware
                    row["Capacity(GB)"] = str(device.capacity_bytes // (1024**3))
                    row["Protocol"] = device.protocol.value
                else:
                    row["SerialNumber"] = "Unknown"
                    row["Model"] = "Unknown"
                    row["Protocol"] = "Unknown"
                    # Populate Status and Reason even if device info is missing
                    row["Status"] = graded.status.value
                    row["FailureReason/Flag"] = self._format_failure_flag(graded)
                    writer.writerow(row)
                    continue # Skip rest if device object is missing

                # Common fields for all protocols (if not error)
                row["Status"] = graded.status.value
                row["FailureReason/Flag"] = self._format_failure_flag(graded)

                poh_hours = self._get_poh_hours(device)
                row["POH_Hours"] = str(poh_hours) if poh_hours is not None else ""
                row["POH_Readable"] = self._format_poh_readable(poh_hours)

                host_reads_gb = self._get_host_reads_gb(device) # Use the correct helper
                row["HostReads(GB)"] = f"{host_reads_gb:.2f}" if host_reads_gb is not None else ""
                host_writes_gb = self._get_host_writes_gb(device) # Use the correct helper
                row["HostWrites(GB)"] = f"{host_writes_gb:.2f}" if host_writes_gb is not None else ""
                row["MaxTemp"] = str(self._get_max_temp(device)) if self._get_max_temp(device) is not None else "" # Handle None
                row["AvgTemp"] = str(self._get_avg_temp(device)) if self._get_avg_temp(device) is not None else "" # Handle None


                # Protocol-specific fields
                if device.protocol in (TransportProtocol.SATA, TransportProtocol.SAS):
                    row["ReallocatedSectors (HDD)"] = self._get_sata_sas_attribute(device, 5, "Reallocated_Sector_Ct", default_val="")
                    row["PendingSectors (HDD)"] = self._get_sata_sas_attribute(device, 197, "Current_Pending_Sector", default_val="")
                    row["PercentUsed (SSD)"] = str(self._get_sata_sas_percent_used(device)) if self._get_sata_sas_percent_used(device) is not None else ""
                    row["AvailableSpare% (SSD)"] = str(self._get_sata_sas_available_spare(device)) if self._get_sata_sas_available_spare(device) is not None else ""

                elif device.protocol == TransportProtocol.NVME:
                    row["PercentUsed (SSD)"] = str(self._get_nvme_percent_used(device)) if self._get_nvme_percent_used(device) is not None else ""
                    row["AvailableSpare% (SSD)"] = str(self._get_nvme_available_spare(device)) if self._get_nvme_available_spare(device) is not None else ""
                    row["MediaErrors (NVMe)"] = str(self._get_nvme_media_errors(device)) if self._get_nvme_media_errors(device) is not None else ""
                    row["WarningTempTime(min)"] = str(self._get_nvme_warning_temp_time(device)) if self._get_nvme_warning_temp_time(device) is not None else ""
                    row["CriticalTempTime(min)"] = str(self._get_nvme_critical_temp_time(device)) if self._get_nvme_critical_temp_time(device) is not None else ""
                    # Max/Avg Temp for NVMe is implicitly handled by _get_max/avg_temp helpers if current temp is available

                writer.writerow(row)

    def _generate_json_report(
        self,
        graded_devices: List[GradedDevice],
        output_dir: Path,
        detailed: bool,
    ) -> None:
        """Generate a JSON report."""
        output_file = output_dir / "device_grades.json"
        logger.info(f"Generating JSON report: {output_file}")

        report = []
        for graded in graded_devices:
            device = graded.device
            report.append({
                "serial_number": device.serial,
                "model": device.model,
                "firmware": device.firmware,
                "capacity_gb": device.capacity_bytes // (1024**3),
                "protocol": device.protocol.value,
                "status": graded.status.value,
                "failure_reason": graded.failure_reason.value if graded.failure_reason else None,
                "flag_reason": graded.flag_reason.value if graded.flag_reason else None,
                "power_on_hours": {
                    "readable": self._format_poh_readable(self._get_poh_hours(device)),
                    "hours": self._get_poh_hours(device),
                },
                "workload_tb_per_year": graded.workload_tb_per_year,
                "smart_data": device.smart_data if detailed else None,
                "nvme_data": device.nvme_data if detailed else None,
                "sas_data": device.sas_data if detailed else None,
            })

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

    def _generate_text_report(
        self,
        graded_devices: List[GradedDevice],
        output_dir: Path,
        detailed: bool,
    ) -> None:
        """Generate a text report."""
        output_file = output_dir / "device_grades.txt"
        logger.info(f"Generating text report: {output_file}")

        with open(output_file, "w") as f:
            for graded in graded_devices:
                device = graded.device
                f.write(f"Device: {device.model} ({device.serial})\n")
                f.write(f"  Protocol: {device.protocol.value}\n")
                f.write(f"  Status: {graded.status.value}\n")
                if graded.failure_reason:
                    f.write(f"  Failure Reason: {graded.failure_reason.value}\n")
                if graded.flag_reason:
                    f.write(f"  Flag Reason: {graded.flag_reason.value}\n")
                f.write(f"  Power On Hours: {self._format_poh_readable(self._get_poh_hours(device))}\n")
                if graded.workload_tb_per_year:
                    f.write(f"  Workload: {graded.workload_tb_per_year:.1f} TB/year\n")
                f.write("\n")

    def _format_failure_flag(self, graded: GradedDevice) -> str:
        """Format failure reason or flag for CSV."""
        if graded.status == DeviceStatus.ERROR and graded.failure_reason:
             return f"ERROR: {graded.failure_reason.value}"
        elif graded.failure_reason:
            return f"FAIL: {graded.failure_reason.value}"
        elif graded.flag_reason:
            return f"FLAG: {graded.flag_reason.value}"
        elif graded.status == DeviceStatus.ERROR:
             return "ERROR: Unknown"
        return ""

    def _format_poh_readable(self, hours: Optional[int]) -> str:
        """Format power-on hours in human-readable format from hours value."""
        if hours is None or hours <= 0:
            return "N/A"
        delta = timedelta(hours=hours)
        years = delta.days // 365
        days = delta.days % 365
        hours_comp = delta.seconds // 3600

        parts = []
        if years:
            parts.append(f"{years}y")
        if days:
            parts.append(f"{days}d")
        if hours_comp:
            parts.append(f"{hours_comp}h")
        return " ".join(parts) if parts else ("0h" if hours == 0 else "N/A")

    def _get_poh_hours(self, device: StorageDevice) -> Optional[int]:
        """Get Power On Hours."""
        poh_hours = None
        if device.smart_data:
            poh_hours = device.smart_data.get("power_on_time", {}).get("hours")

        if device.protocol == TransportProtocol.NVME and device.nvme_data:
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                nvme_poh = health_log.get("power_on_hours")
                if nvme_poh is not None:
                    poh_hours = nvme_poh # Prefer NVMe value if available
            else:
                 logger.warning(f"Device {device.serial}: NVMe health log is not a dict or missing for POH. Type: {type(health_log)}")

        if poh_hours is not None:
            try:
                return int(poh_hours)
            except (ValueError, TypeError):
                logger.warning(f"Device {device.serial}: Invalid POH value '{poh_hours}' encountered.")
                return None
        return None

    def _get_sata_sas_helper(self, smart_data: Optional[dict], attr_id: int, attr_name: str) -> Optional[dict]:
        """Helper to safely get SATA/SAS attribute dict."""
        if not smart_data or "ata_smart_attributes" not in smart_data:
            return None
        attributes = smart_data.get("ata_smart_attributes", {}).get("table", [])
        for attr in attributes:
            if attr.get("id") == attr_id:
                return attr
            if attr_name and attr.get("name") == attr_name:
                 return attr
        return None

    def _get_sata_sas_attribute(self, device: StorageDevice, attr_id: int, attr_name: str, default_val="") -> str:
        """Safely get a specific SATA/SAS SMART attribute's raw value string."""
        if not device.smart_data:
            return default_val
        attr = self._get_sata_sas_helper(device.smart_data, attr_id, attr_name)
        if not attr:
            return default_val

        # Prioritize raw string if available, else raw value
        raw_data = attr.get("raw", {})
        if "string" in raw_data:
             return str(raw_data["string"]).strip()
        elif "value" in raw_data:
             return str(raw_data["value"])
        else: # Fallback to normalized value if raw is missing?
             return str(attr.get("value", default_val))

    def _get_percent_used(self, device: StorageDevice) -> str:
        """Get percentage used from device data safely, returns string."""
        percent_used = None
        if device.nvme_data:
            logger.debug(f"Device {device.serial}: Trying NVMe PercentUsed. nvme_data available: True")
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                logger.debug(f"Device {device.serial}: Found health_log dict.")
                percent_used = health_log.get("percentage_used")
                logger.debug(f"Device {device.serial}: PercentUsed from health_log: {percent_used}")
            else:
                logger.warning(f"Device {device.serial}: health_log is not a dict or missing for PercentUsed. Type: {type(health_log)}")
        elif not device.smart_data: # Only log if not SATA/SAS either
            logger.debug(f"Device {device.serial}: Trying NVMe PercentUsed. nvme_data available: False")

        # Try SATA/SAS SSD if NVMe not applicable/found
        if percent_used is None and device.smart_data:
            # Check if it's likely an SSD (e.g., has wear level attribute)
            wear_level_attr = self._get_sata_sas_helper(device.smart_data, 177, "Wear_Leveling_Count")
            life_left_attr = self._get_sata_sas_helper(device.smart_data, 231, "SSD_Life_Left")
            lifetime_used_attr = self._get_sata_sas_helper(device.smart_data, 233, "Media_Wearout_Indicator")

            if life_left_attr:
                 life_left_val = life_left_attr.get("value")
                 if life_left_val is not None:
                     try: percent_used = 100 - int(life_left_val)
                     except (ValueError, TypeError): pass
            elif lifetime_used_attr:
                 raw_val = lifetime_used_attr.get("raw", {}).get("value")
                 if raw_val is not None:
                     try: percent_used = int(raw_val)
                     except (ValueError, TypeError): pass
            # Fallback to wear leveling is generally too unreliable

        return str(percent_used) if percent_used is not None else ""

    def _get_available_spare(self, device: StorageDevice) -> str:
        """Get available spare percentage from device data safely, returns string."""
        available_spare = None
        if device.nvme_data:
            logger.debug(f"Device {device.serial}: Trying NVMe AvailableSpare. nvme_data available: True")
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                logger.debug(f"Device {device.serial}: Found health_log dict.")
                available_spare = health_log.get("available_spare")
                logger.debug(f"Device {device.serial}: AvailableSpare from health_log: {available_spare}")
            else:
                logger.warning(f"Device {device.serial}: health_log is not a dict or missing for AvailableSpare. Type: {type(health_log)}")
        elif not device.smart_data:
            logger.debug(f"Device {device.serial}: Trying NVMe AvailableSpare. nvme_data available: False")

        # Try SATA/SAS SSD if NVMe not applicable/found
        if available_spare is None and device.smart_data:
            # Common attribute ID 173 (Available Reserved Space) - normalized value
            spare_attr = self._get_sata_sas_helper(device.smart_data, 173, "Available_Reservd_Space")
            if spare_attr:
                 available_spare = spare_attr.get("value") # Normalized value usually (0-100)

        return str(available_spare) if available_spare is not None else ""

    def _get_host_reads(self, device: StorageDevice) -> Optional[int]:
        """Get host reads in bytes from device data safely."""
        reads_bytes = None
        if device.nvme_data:
            logger.debug(f"Device {device.serial}: Trying NVMe HostReads. nvme_data available: True")
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                logger.debug(f"Device {device.serial}: Found health_log dict.")
                units = health_log.get("data_units_read")
                logger.debug(f"Device {device.serial}: DataUnitsRead from health_log: {units}")
                if units is not None:
                     try: reads_bytes = int(units) * 512 * 1000
                     except (ValueError, TypeError): pass
            else:
                logger.warning(f"Device {device.serial}: health_log is not a dict or missing for HostReads. Type: {type(health_log)}")
        elif not device.smart_data:
            logger.debug(f"Device {device.serial}: Trying NVMe HostReads. nvme_data available: False")

        # Try SATA/SAS if NVMe not applicable/found
        if reads_bytes is None and device.smart_data:
            # Check for Total_LBAs_Read (ID 242)
            lbas_read_attr = self._get_sata_sas_helper(device.smart_data, 242, "Total_LBAs_Read")
            if lbas_read_attr:
                raw_val = lbas_read_attr.get("raw", {}).get("value")
                if raw_val is not None:
                    try:
                        # Determine block size (usually 512 for SATA)
                        block_size = device.smart_data.get("logical_block_size", 512)
                        reads_bytes = int(raw_val) * block_size
                    except (ValueError, TypeError): pass
            else:
                # Fallback to vendor specific MiB/GiB attributes if LBA count absent
                reads_mib_attr = self._get_sata_sas_helper(device.smart_data, -1, "Host_Reads_MiB")
                if reads_mib_attr:
                    raw_val = reads_mib_attr.get("raw", {}).get("value")
                    if raw_val is not None:
                        try: reads_bytes = int(raw_val) * 1024 * 1024
                        except (ValueError, TypeError): pass
                # Add more vendor specific checks if needed (e.g., Host_Reads_32MiB)

        return reads_bytes

    def _get_host_writes(self, device: StorageDevice) -> Optional[int]:
        """Get host writes in bytes from device data safely."""
        writes_bytes = None
        if device.nvme_data:
            logger.debug(f"Device {device.serial}: Trying NVMe HostWrites. nvme_data available: True")
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                logger.debug(f"Device {device.serial}: Found health_log dict.")
                units = health_log.get("data_units_written")
                logger.debug(f"Device {device.serial}: DataUnitsWritten from health_log: {units}")
                if units is not None:
                     try: writes_bytes = int(units) * 512 * 1000
                     except (ValueError, TypeError): pass
            else:
                logger.warning(f"Device {device.serial}: health_log is not a dict or missing for HostWrites. Type: {type(health_log)}")
        elif not device.smart_data:
            logger.debug(f"Device {device.serial}: Trying NVMe HostWrites. nvme_data available: False")

        # Try SATA/SAS if NVMe not applicable/found
        if writes_bytes is None and device.smart_data:
            # Check for Total_LBAs_Written (ID 241)
            lbas_written_attr = self._get_sata_sas_helper(device.smart_data, 241, "Total_LBAs_Written")
            if lbas_written_attr:
                raw_val = lbas_written_attr.get("raw", {}).get("value")
                if raw_val is not None:
                    try:
                        block_size = device.smart_data.get("logical_block_size", 512)
                        writes_bytes = int(raw_val) * block_size
                    except (ValueError, TypeError): pass
            else:
                # Fallback to vendor specific MiB/GiB attributes
                writes_mib_attr = self._get_sata_sas_helper(device.smart_data, -1, "Host_Writes_MiB")
                if writes_mib_attr:
                    raw_val = writes_mib_attr.get("raw", {}).get("value")
                    if raw_val is not None:
                        try: writes_bytes = int(raw_val) * 1024 * 1024
                        except (ValueError, TypeError): pass
                # Add more vendor specific checks

        return writes_bytes

    def _get_max_temp(self, device: StorageDevice) -> str:
        """Get maximum temperature from device data safely, returns string."""
        # For Max Temp, use current temp as a proxy as lifetime max is hard to parse reliably
        current_temp = self._get_current_temp(device)
        return str(current_temp) if current_temp is not None else ""

    def _get_current_temp(self, device: StorageDevice) -> Optional[int]:
        """Helper to get current temperature."""
        current_temp = None
        # Try NVMe first
        if device.nvme_data:
            logger.debug(f"Device {device.serial}: Trying NVMe CurrentTemp. nvme_data available: True")
            # Check health log first, then top-level temp object
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                logger.debug(f"Device {device.serial}: Found health_log dict.")
                current_temp = health_log.get("temperature")
                logger.debug(f"Device {device.serial}: Temp from health_log: {current_temp}")
            if current_temp is None:
                temp_obj = device.nvme_data.get("temperature")
                if isinstance(temp_obj, dict):
                    current_temp = temp_obj.get("current")
            # Fallback for other possible NVMe keys (less standard)
            if current_temp is None:
                current_temp = device.nvme_data.get("Composite Temperature") # From nvme-cli, maybe in smartctl?
            if current_temp is None:
                sensors = device.nvme_data.get("temperature_sensors", [])
                if sensors and isinstance(sensors, list) and len(sensors) > 0:
                    current_temp = sensors[0].get("current")

        # Try SATA/SAS if NVMe not found
        if current_temp is None and device.smart_data:
            # Check raw value of 194 first
            temp_celsius_attr = self._get_sata_sas_helper(device.smart_data, 194, "Temperature_Celsius")
            if temp_celsius_attr:
                val = temp_celsius_attr.get("value") # Normalized value
                if val is not None:
                    try: current_temp = int(val)
                    except (ValueError, TypeError): pass

        # Final conversion check
        if current_temp is not None:
             try: return int(current_temp)
             except (ValueError, TypeError): pass
        return None

    def _get_avg_temp(self, device: StorageDevice) -> str:
        """Get average temperature proxy (current temp) from device data safely, returns string."""
        # This function now just calls _get_current_temp, logging is inside that helper
        current_temp = self._get_current_temp(device)
        return str(current_temp) if current_temp is not None else ""

    def _format_bytes_gb(self, bytes_val: Optional[int]) -> str:
        """Format bytes to GB, handling None."""
        if bytes_val is None or bytes_val < 0:
            return ""
        return f"{bytes_val / (1024**3):.2f}"

    def _get_nvme_percent_used(self, device: StorageDevice) -> Optional[int]:
        """Get NVMe Percentage Used."""
        if device.protocol == TransportProtocol.NVME and device.nvme_data:
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                percent_used = health_log.get("percentage_used")
                if percent_used is not None:
                     try:
                         return int(percent_used)
                     except (ValueError, TypeError):
                        logger.warning(f"Device {device.serial}: Invalid PercentUsed value '{percent_used}'.")
                        return None
                logger.debug(f"Device {device.serial}: PercentUsed from health_log: {percent_used}")
            else:
                 logger.warning(f"Device {device.serial}: health_log is not a dict or missing for PercentUsed. Type: {type(health_log)}")
        return None

    def _get_nvme_available_spare(self, device: StorageDevice) -> Optional[int]:
        """Get NVMe Available Spare Percentage."""
        if device.protocol == TransportProtocol.NVME and device.nvme_data:
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                # Try both keys observed
                available_spare = health_log.get("available_spare", health_log.get("avail_spare"))
                if available_spare is not None:
                     try:
                         return int(available_spare)
                     except (ValueError, TypeError):
                        logger.warning(f"Device {device.serial}: Invalid AvailableSpare value '{available_spare}'.")
                        return None
                logger.debug(f"Device {device.serial}: AvailableSpare from health_log: {available_spare}")
            else:
                logger.warning(f"Device {device.serial}: health_log is not a dict or missing for AvailableSpare. Type: {type(health_log)}")
        return None

    def _get_nvme_host_reads_gb(self, device: StorageDevice) -> Optional[float]:
        """Get NVMe Host Reads in GB."""
        if device.protocol == TransportProtocol.NVME and device.nvme_data:
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                units = health_log.get("data_units_read")
                if units is not None:
                    try:
                        units_int = int(units)
                        # Convert (512 * 1000 byte units) to GB
                        return (units_int * 512 * 1000) / (1024**3)
                    except (ValueError, TypeError):
                        logger.warning(f"Device {device.serial}: Invalid DataUnitsRead value '{units}'.")
                        return None
                logger.debug(f"Device {device.serial}: DataUnitsRead from health_log: {units}")
            else:
                 logger.warning(f"Device {device.serial}: health_log is not a dict or missing for HostReads. Type: {type(health_log)}")
        return None

    def _get_nvme_host_writes_gb(self, device: StorageDevice) -> Optional[float]:
        """Get NVMe Host Writes in GB."""
        if device.protocol == TransportProtocol.NVME and device.nvme_data:
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                units = health_log.get("data_units_written")
                if units is not None:
                    try:
                        units_int = int(units)
                        # Convert (512 * 1000 byte units) to GB
                        return (units_int * 512 * 1000) / (1024**3)
                    except (ValueError, TypeError):
                        logger.warning(f"Device {device.serial}: Invalid DataUnitsWritten value '{units}'.")
                        return None
                logger.debug(f"Device {device.serial}: DataUnitsWritten from health_log: {units}")
            else:
                logger.warning(f"Device {device.serial}: health_log is not a dict or missing for HostWrites. Type: {type(health_log)}")
        return None

    def _get_nvme_current_temp(self, device: StorageDevice) -> Optional[int]:
        """Get NVMe Current Temperature in Celsius."""
        if device.protocol == TransportProtocol.NVME and device.nvme_data:
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                current_temp_kelvin = health_log.get("temperature")
                if current_temp_kelvin is not None:
                    try:
                        # Convert Kelvin to Celsius
                        return int(current_temp_kelvin) - 273
                    except (ValueError, TypeError):
                        logger.warning(f"Device {device.serial}: Invalid Temperature value '{current_temp_kelvin}'.")
                        return None
                logger.debug(f"Device {device.serial}: Temp from health_log: {current_temp_kelvin}")
            else:
                logger.warning(f"Device {device.serial}: health_log is not a dict or missing for CurrentTemp. Type: {type(health_log)}")
        return None

    def _get_nvme_media_errors(self, device: StorageDevice) -> Optional[int]:
        """Get NVMe Media and Data Integrity Errors."""
        if device.protocol == TransportProtocol.NVME and device.nvme_data:
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                media_errors = health_log.get("media_errors")
                if media_errors is not None:
                    try:
                        return int(media_errors)
                    except (ValueError, TypeError):
                         logger.warning(f"Device {device.serial}: Invalid MediaErrors value '{media_errors}'.")
                         return None
            else:
                 logger.warning(f"Device {device.serial}: health_log is not a dict or missing for MediaErrors. Type: {type(health_log)}")
        return None

    def _get_nvme_warning_temp_time(self, device: StorageDevice) -> Optional[int]:
        """Get NVMe Warning Composite Temperature Time (minutes)."""
        if device.protocol == TransportProtocol.NVME and device.nvme_data:
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                warning_time = health_log.get("warning_temp_time")
                if warning_time is not None:
                    try:
                        return int(warning_time)
                    except (ValueError, TypeError):
                         logger.warning(f"Device {device.serial}: Invalid WarningTempTime value '{warning_time}'.")
                         return None
            else:
                 logger.warning(f"Device {device.serial}: health_log is not a dict or missing for WarningTempTime. Type: {type(health_log)}")
        return None

    def _get_nvme_critical_temp_time(self, device: StorageDevice) -> Optional[int]:
        """Get NVMe Critical Composite Temperature Time (minutes)."""
        if device.protocol == TransportProtocol.NVME and device.nvme_data:
            health_log = device.nvme_data.get("nvme_smart_health_information_log")
            if isinstance(health_log, dict):
                critical_time = health_log.get("critical_comp_time")
                if critical_time is not None:
                     try:
                         return int(critical_time)
                     except (ValueError, TypeError):
                         logger.warning(f"Device {device.serial}: Invalid CriticalTempTime value '{critical_time}'.")
                         return None
            else:
                 logger.warning(f"Device {device.serial}: health_log is not a dict or missing for CriticalTempTime. Type: {type(health_log)}")
        return None