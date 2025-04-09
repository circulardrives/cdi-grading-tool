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
from typing import List

from cdi_health.core.grading_engine import GradedDevice

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
                device = graded.device
                row = {
                    "SerialNumber": device.serial,
                    "Model": device.model,
                    "Firmware": device.firmware,
                    "Capacity(GB)": device.capacity_bytes // (1024**3),
                    "Protocol": device.protocol.value,
                    "Status": graded.status.value,
                    "FailureReason/Flag": self._format_failure_flag(graded),
                    "POH_Readable": self._format_poh_readable(device),
                    "POH_Hours": self._get_poh_hours(device),
                    "ReallocatedSectors (HDD)": device.smart_data.get("reallocated_sectors", ""),
                    "PendingSectors (HDD)": device.smart_data.get("pending_sectors", ""),
                    "PercentUsed (SSD)": self._get_percent_used(device),
                    "AvailableSpare% (SSD)": self._get_available_spare(device),
                    "MediaErrors (NVMe)": device.nvme_data.get("media_errors", ""),
                    "HostReads(GB)": self._format_bytes_gb(self._get_host_reads(device)),
                    "HostWrites(GB)": self._format_bytes_gb(self._get_host_writes(device)),
                    "MaxTemp": self._get_max_temp(device),
                    "AvgTemp": self._get_avg_temp(device),
                    "WarningTempTime(min)": device.nvme_data.get("warning_temp_time", ""),
                    "CriticalTempTime(min)": device.nvme_data.get("critical_temp_time", ""),
                }
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
                    "readable": self._format_poh_readable(device),
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
                f.write(f"  Power On Hours: {self._format_poh_readable(device)}\n")
                if graded.workload_tb_per_year:
                    f.write(f"  Workload: {graded.workload_tb_per_year:.1f} TB/year\n")
                f.write("\n")

    def _format_failure_flag(self, graded: GradedDevice) -> str:
        """Format failure reason or flag for CSV."""
        if graded.failure_reason:
            return f"FAIL: {graded.failure_reason.value}"
        elif graded.flag_reason:
            return f"FLAG: {graded.flag_reason.value}"
        return ""

    def _format_poh_readable(self, device: StorageDevice) -> str:
        """Format power-on hours in human-readable format."""
        hours = self._get_poh_hours(device)
        if not hours:
            return ""

        delta = timedelta(hours=hours)
        years = delta.days // 365
        days = delta.days % 365
        hours = delta.seconds // 3600

        parts = []
        if years:
            parts.append(f"{years}y")
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        return " ".join(parts) if parts else "0h"

    def _get_poh_hours(self, device: StorageDevice) -> int:
        """Get power-on hours from device data."""
        return (
            device.smart_data.get("power_on_hours", 0) or
            device.nvme_data.get("power_on_hours", 0) or
            0
        )

    def _get_percent_used(self, device: StorageDevice) -> int:
        """Get percentage used from device data."""
        return (
            device.smart_data.get("percentage_used", 0) or
            device.nvme_data.get("percentage_used", 0) or
            0
        )

    def _get_available_spare(self, device: StorageDevice) -> int:
        """Get available spare percentage from device data."""
        return (
            device.smart_data.get("available_spare", 100) or
            device.nvme_data.get("available_spare", 100) or
            100
        )

    def _get_host_reads(self, device: StorageDevice) -> int:
        """Get host reads in bytes from device data."""
        return (
            device.smart_data.get("host_reads_bytes", 0) or
            device.nvme_data.get("host_reads_bytes", 0) or
            0
        )

    def _get_host_writes(self, device: StorageDevice) -> int:
        """Get host writes in bytes from device data."""
        return (
            device.smart_data.get("host_writes_bytes", 0) or
            device.nvme_data.get("host_writes_bytes", 0) or
            0
        )

    def _get_max_temp(self, device: StorageDevice) -> int:
        """Get maximum temperature from device data."""
        return (
            device.smart_data.get("max_temp", 0) or
            device.nvme_data.get("max_temp", 0) or
            0
        )

    def _get_avg_temp(self, device: StorageDevice) -> int:
        """Get average temperature from device data."""
        return (
            device.smart_data.get("avg_temp", 0) or
            device.nvme_data.get("avg_temp", 0) or
            0
        )

    def _format_bytes_gb(self, bytes: int) -> float:
        """Format bytes as GB."""
        return bytes / (1024**3)