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
                row = {key: "N/A" for key in fieldnames} # Initialize row with N/A

                if graded.device: # Basic info if device exists
                    row["SerialNumber"] = graded.device.serial
                    row["Model"] = graded.device.model
                    row["Firmware"] = graded.device.firmware
                    row["Capacity(GB)"] = str(graded.device.capacity_bytes // (1024**3))
                    row["Protocol"] = graded.device.protocol.value
                else:
                    row["SerialNumber"] = "Unknown"
                    row["Model"] = "Unknown"
                    # Keep others as N/A

                row["Status"] = graded.status.value
                row["FailureReason/Flag"] = self._format_failure_flag(graded)

                # If status is ERROR, we already filled with N/A or basic info, so skip further processing
                if graded.status == DeviceStatus.ERROR:
                    writer.writerow(row)
                    continue

                # Proceed for non-errored devices
                device = graded.device

                # Safely get and format values, defaulting to empty string if None/Error
                poh_hours = self._get_poh_hours(device)
                row["POH_Hours"] = str(poh_hours) if poh_hours is not None else ""
                row["POH_Readable"] = self._format_poh_readable(poh_hours)
                row["ReallocatedSectors (HDD)"] = self._get_sata_sas_attribute(device, 5, "Reallocated_Sector_Ct", default_val="")
                row["PendingSectors (HDD)"] = self._get_sata_sas_attribute(device, 197, "Current_Pending_Sector", default_val="")
                row["PercentUsed (SSD)"] = self._get_percent_used(device)
                row["AvailableSpare% (SSD)"] = self._get_available_spare(device)
                row["MediaErrors (NVMe)"] = str(device.nvme_data.get("media_errors", "")) if device.nvme_data else ""
                row["WarningTempTime(min)"] = str(device.nvme_data.get("warning_temp_time", "")) if device.nvme_data else ""
                row["CriticalTempTime(min)"] = str(device.nvme_data.get("critical_temp_time", "")) if device.nvme_data else ""
                row["HostReads(GB)"] = self._format_bytes_gb(self._get_host_reads(device))
                row["HostWrites(GB)"] = self._format_bytes_gb(self._get_host_writes(device))
                row["MaxTemp"] = self._get_max_temp(device)
                row["AvgTemp"] = self._get_avg_temp(device)

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
        """Get power-on hours from device data safely."""
        poh = None
        # Try SATA/SAS first (Attribute ID 9)
        if device.smart_data:
            power_on_time_data = device.smart_data.get("power_on_time")
            if isinstance(power_on_time_data, dict):
                poh = power_on_time_data.get("hours")
            # Fallback: Check SMART attributes table directly for ID 9
            if poh is None:
                 poh_attr = self._get_sata_sas_helper(device.smart_data, 9, "Power_On_Hours")
                 raw_val = poh_attr.get("raw", {}).get("value") if poh_attr else None
                 if raw_val is not None:
                     try: poh = int(raw_val)
                     except (ValueError, TypeError): pass

        # Try NVMe if SATA/SAS not found or not applicable
        if poh is None and device.nvme_data:
            poh = device.nvme_data.get("power_on_hours")

        # Final conversion check
        if poh is not None:
            try:
                return int(poh)
            except (ValueError, TypeError):
                pass
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
        # Try NVMe first
        if device.nvme_data:
             percent_used = device.nvme_data.get("percentage_used")

        # Try SATA/SAS SSD if NVMe not applicable
        if percent_used is None and device.smart_data:
            # Check if it's likely an SSD (e.g., has wear level attribute)
            wear_level_attr = self._get_sata_sas_helper(device.smart_data, 177, "Wear_Leveling_Count")
            life_left_attr = self._get_sata_sas_helper(device.smart_data, 231, "SSD_Life_Left")
            lifetime_used_attr = self._get_sata_sas_helper(device.smart_data, 233, "Media_Wearout_Indicator") # Another common one

            if life_left_attr:
                 # Use 'SSD Life Left' (normalized value, 100=new, 0=used)
                 life_left_val = life_left_attr.get("value")
                 if life_left_val is not None:
                     try: percent_used = 100 - int(life_left_val)
                     except (ValueError, TypeError): pass
            elif lifetime_used_attr:
                 # Use 'Media Wearout Indicator' (often raw value is percentage used)
                 raw_val = lifetime_used_attr.get("raw", {}).get("value")
                 if raw_val is not None:
                     try: percent_used = int(raw_val)
                     except (ValueError, TypeError): pass
            elif wear_level_attr: # Fallback: infer from wear leveling? Less reliable
                 pass # Logic too complex/unreliable for generic case

        return str(percent_used) if percent_used is not None else ""

    def _get_available_spare(self, device: StorageDevice) -> str:
        """Get available spare percentage from device data safely, returns string."""
        available_spare = None
        # Try NVMe first
        if device.nvme_data:
            available_spare = device.nvme_data.get("available_spare")
            # NVMe spec: value is percentage *remaining*. Convert if necessary based on PRD needs.
            # Assuming the value is directly the percentage remaining (0-100)

        # Try SATA/SAS SSD if NVMe not applicable
        if available_spare is None and device.smart_data:
            # Common attribute ID 173 (Available Reserved Space) - normalized value
            spare_attr = self._get_sata_sas_helper(device.smart_data, 173, "Available_Reservd_Space")
            if spare_attr:
                 available_spare = spare_attr.get("value") # Normalized value usually (0-100)

        return str(available_spare) if available_spare is not None else ""

    def _get_host_reads(self, device: StorageDevice) -> Optional[int]:
        """Get host reads in bytes from device data safely."""
        reads_bytes = None
        # Try NVMe first
        if device.nvme_data:
            units = device.nvme_data.get("data_units_read")
            if units is not None:
                 try: reads_bytes = int(units) * 512 * 1000 # 512-byte units * 1000
                 except (ValueError, TypeError): pass

        # Try SATA/SAS if NVMe not applicable
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
        # Try NVMe first
        if device.nvme_data:
            units = device.nvme_data.get("data_units_written")
            if units is not None:
                 try: writes_bytes = int(units) * 512 * 1000 # 512-byte units * 1000
                 except (ValueError, TypeError): pass

        # Try SATA/SAS if NVMe not applicable
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
        max_temp = None
        current_temp = None

        # Try NVMe first
        if device.nvme_data:
            # NVMe reports current temp, may report max over lifetime separately
            current_temp = device.nvme_data.get("temperature")
            # Check for a dedicated max temp field if available in standard NVMe logs (less common)
            # Example: max_temp = device.nvme_data.get("maximum_temperature_lifetime")

        # Try SATA/SAS
        if device.smart_data:
            # Attribute 194 usually has current temp in normalized 'value'
            temp_celsius_attr = self._get_sata_sas_helper(device.smart_data, 194, "Temperature_Celsius")
            if temp_celsius_attr:
                 val = temp_celsius_attr.get("value")
                 if val is not None:
                     try: current_temp = int(val)
                     except (ValueError, TypeError): pass
                 # The raw value of 194 sometimes contains max temp
                 raw_val = temp_celsius_attr.get("raw", {}).get("value")
                 if raw_val is not None:
                      raw_str = str(raw_val)
                      try:
                           # Example: "30 (Min/Max 25/40)" or "30 C"
                           if "Min/Max" in raw_str and len(raw_str.split("/")) > 2:
                               max_temp = int(raw_str.split("/")[2].split(")")[0].strip())
                           # Add other parsing logic if needed
                      except (ValueError, IndexError, TypeError): pass

            # Attribute 190 (Airflow_Temperature_Cel) sometimes used for max
            if max_temp is None:
                 airflow_temp_attr = self._get_sata_sas_helper(device.smart_data, 190, "Airflow_Temperature_Cel")
                 if airflow_temp_attr:
                      # Often raw value is max temp
                      raw_val = airflow_temp_attr.get("raw", {}).get("value")
                      if raw_val is not None:
                          try: max_temp = int(str(raw_val).split()[0]) # Take first number
                          except (ValueError, IndexError, TypeError): pass

        # If max_temp couldn't be found, use current_temp as a fallback (less ideal)
        final_temp = max_temp if max_temp is not None else current_temp
        return str(final_temp) if final_temp is not None else ""

    def _get_avg_temp(self, device: StorageDevice) -> str:
        """Get average temperature proxy (current temp) from device data safely, returns string."""
        # SMART typically only reports current temp. Use that as proxy for average.
        current_temp = None
        # Try NVMe first
        if device.nvme_data:
            current_temp = device.nvme_data.get("temperature")

        # Try SATA/SAS
        if current_temp is None and device.smart_data:
            temp_celsius_attr = self._get_sata_sas_helper(device.smart_data, 194, "Temperature_Celsius")
            if temp_celsius_attr:
                 val = temp_celsius_attr.get("value") # Normalized value often C
                 if val is not None:
                     try: current_temp = int(val)
                     except (ValueError, TypeError): pass

        return str(current_temp) if current_temp is not None else ""

    def _format_bytes_gb(self, bytes_val: Optional[int]) -> str:
        """Format bytes to GB, handling None."""
        if bytes_val is None or bytes_val < 0:
            return ""
        return f"{bytes_val / (1024**3):.2f}"