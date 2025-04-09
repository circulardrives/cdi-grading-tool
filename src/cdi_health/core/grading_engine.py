"""
Grading Engine

This module implements the grading logic for storage devices based on the PRD.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from cdi_health.core.device_manager import StorageDevice, TransportProtocol

logger = logging.getLogger(__name__)

class DeviceStatus(Enum):
    """Device grading status."""
    PASS = "pass"
    FAIL = "fail"
    FLAGGED = "flagged"
    ERROR = "error"

class FlagReason(Enum):
    """Reasons for flagging a device."""
    HEAVY_USE = "heavy_use"
    TEMP_WARNING = "temp_warning"

class FailureReason(Enum):
    """Reasons for failing a device."""
    FAILED_SELF_TEST = "failed_self_test"
    PENDING_SECTORS = "pending_sectors"
    REALLOCATED_SECTORS = "reallocated_sectors"
    PERCENT_USED = "percent_used"
    AVAILABLE_SPARE = "available_spare"
    MEDIA_ERRORS = "media_errors"
    CRITICAL_TEMP = "critical_temp"
    DATA_READ_ERROR = "data_read_error"

@dataclass
class GradedDevice:
    """Graded storage device information."""
    device: StorageDevice
    status: DeviceStatus
    failure_reason: Optional[FailureReason] = None
    flag_reason: Optional[FlagReason] = None
    workload_tb_per_year: Optional[float] = None

class GradingEngine:
    """Implements the grading logic for storage devices."""

    # Thresholds from PRD
    PENDING_SECTORS_THRESHOLD = 10
    REALLOCATED_SECTORS_THRESHOLD = 10
    PERCENT_USED_THRESHOLD = 100
    AVAILABLE_SPARE_THRESHOLD = 97
    WORKLOAD_THRESHOLD_TB_PER_YEAR = 550
    MEDIA_ERRORS_THRESHOLD = 10  # TBD in PRD
    CRITICAL_TEMP_TIME_THRESHOLD = 0  # TBD in PRD
    WARNING_TEMP_TIME_THRESHOLD = 60  # TBD in PRD

    def grade_devices(self, devices: List[StorageDevice]) -> List[GradedDevice]:
        """Grade a list of storage devices."""
        return [self._grade_device(device) for device in devices]

    def _grade_device(self, device: StorageDevice) -> GradedDevice:
        """Grade a single storage device."""
        try:
            # Check for data read errors
            if not device.smart_data and not device.nvme_data:
                return GradedDevice(
                    device=device,
                    status=DeviceStatus.ERROR,
                    failure_reason=FailureReason.DATA_READ_ERROR,
                )

            # Check for failed self-tests
            if self._has_failed_self_test(device):
                return GradedDevice(
                    device=device,
                    status=DeviceStatus.FAIL,
                    failure_reason=FailureReason.FAILED_SELF_TEST,
                )

            # Protocol-specific checks
            if device.protocol == TransportProtocol.NVME:
                return self._grade_nvme_device(device)
            else:  # SATA or SAS
                return self._grade_sata_sas_device(device)

        except Exception as e:
            logger.error(f"Error grading device {device.serial}: {e}")
            return GradedDevice(
                device=device,
                status=DeviceStatus.ERROR,
                failure_reason=FailureReason.DATA_READ_ERROR,
            )

    def _grade_nvme_device(self, device: StorageDevice) -> GradedDevice:
        """Grade an NVMe device."""
        # Check if NVMe data is available
        if device.nvme_data is None:
            logger.warning(f"Missing NVMe data for device {device.serial}. Marking as error.")
            return GradedDevice(
                device=device,
                status=DeviceStatus.ERROR,
                failure_reason=FailureReason.DATA_READ_ERROR,
            )

        # Check percentage used
        if device.nvme_data.get("percentage_used", 0) > self.PERCENT_USED_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.PERCENT_USED,
            )

        # Check available spare
        if device.nvme_data.get("available_spare", 100) <= self.AVAILABLE_SPARE_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.AVAILABLE_SPARE,
            )

        # Check media errors
        if device.nvme_data.get("media_errors", 0) > self.MEDIA_ERRORS_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.MEDIA_ERRORS,
            )

        # Check critical temperature time
        if device.nvme_data.get("critical_temp_time", 0) > self.CRITICAL_TEMP_TIME_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.CRITICAL_TEMP,
            )

        # Check warning temperature time
        if device.nvme_data.get("warning_temp_time", 0) > self.WARNING_TEMP_TIME_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.PASS,
                flag_reason=FlagReason.TEMP_WARNING,
            )

        # Check workload
        workload = self._calculate_workload(device)
        if workload > self.WORKLOAD_THRESHOLD_TB_PER_YEAR:
            return GradedDevice(
                device=device,
                status=DeviceStatus.PASS,
                flag_reason=FlagReason.HEAVY_USE,
                workload_tb_per_year=workload,
            )

        return GradedDevice(device=device, status=DeviceStatus.PASS)

    def _grade_sata_sas_device(self, device: StorageDevice) -> GradedDevice:
        """Grade a SATA or SAS device."""
        # Check if SMART data is available
        if device.smart_data is None:
            logger.warning(f"Missing SMART data for device {device.serial}. Marking as error.")
            return GradedDevice(
                device=device,
                status=DeviceStatus.ERROR,
                failure_reason=FailureReason.DATA_READ_ERROR,
            )

        # Check pending sectors
        # Use .get with default 0 in case the attribute is missing in the dict
        if device.smart_data.get("ata_smart_attributes", {}).get("table", [])[4].get("raw", {}).get("value", 0) > self.PENDING_SECTORS_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.PENDING_SECTORS,
            )

        # Check reallocated sectors
        # Use .get with default 0
        if device.smart_data.get("ata_smart_attributes", {}).get("table", [])[5].get("raw", {}).get("value", 0) > self.REALLOCATED_SECTORS_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.REALLOCATED_SECTORS,
            )

        # Check percentage used (for SSDs)
        # Use .get with default 0
        percentage_used = 0
        for attr in device.smart_data.get("ata_smart_attributes", {}).get("table", []):
            if attr.get("name") == "Percent_Lifetime_Used": # Common name, might need adjustment
                percentage_used = attr.get("raw", {}).get("value", 0)
                break
        if percentage_used > self.PERCENT_USED_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.PERCENT_USED,
            )

        # Check available spare (for SSDs)
        # Use .get with default 100
        available_spare = 100
        for attr in device.smart_data.get("ata_smart_attributes", {}).get("table", []):
             if attr.get("name") == "Available_Reservd_Space": # Common name, might need adjustment
                available_spare = attr.get("value", 100)
                break
        if available_spare <= self.AVAILABLE_SPARE_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.AVAILABLE_SPARE,
            )

        # Check workload
        workload = self._calculate_workload(device)
        if workload > self.WORKLOAD_THRESHOLD_TB_PER_YEAR:
            return GradedDevice(
                device=device,
                status=DeviceStatus.PASS,
                flag_reason=FlagReason.HEAVY_USE,
                workload_tb_per_year=workload,
            )

        return GradedDevice(device=device, status=DeviceStatus.PASS)

    def _has_failed_self_test(self, device: StorageDevice) -> bool:
        """Check if a device has failed self-tests."""
        # TODO: Implement self-test history checking
        return False

    def _calculate_workload(self, device: StorageDevice) -> float:
        """Calculate workload in TB/year."""
        host_reads = 0
        host_writes = 0
        poh_hours = 0

        # Safely get data from smart_data if available
        if device.smart_data:
            # Example: Assuming smartctl JSON output has these keys
            # Adjust keys based on actual smartctl JSON structure
            # These might be nested within ata_smart_data or similar
            host_reads = device.smart_data.get("power_on_time", {}).get("host_reads_mib", 0) * 1024 * 1024 # Example structure
            host_writes = device.smart_data.get("power_on_time", {}).get("host_writes_mib", 0) * 1024 * 1024 # Example structure
            poh_hours = device.smart_data.get("power_on_time", {}).get("hours", 0)

        # Safely get data from nvme_data if available (and potentially overwrite/add)
        if device.nvme_data:
            host_reads = device.nvme_data.get("data_units_read", 0) * 512 * 1000 # Units are 512-byte blocks * 1000
            host_writes = device.nvme_data.get("data_units_written", 0) * 512 * 1000 # Units are 512-byte blocks * 1000
            poh_hours = device.nvme_data.get("power_on_hours", poh_hours) # Use NVMe if available, else keep SATA/SAS value

        total_bytes = host_reads + host_writes
        if not poh_hours:
            logger.warning(f"Power-on hours not available for device {device.serial}. Cannot calculate workload.")
            return 0.0

        # Convert to TB/year
        poh_years = poh_hours / (24 * 365.25) # Use 365.25 for leap years
        if poh_years <= 0:
             logger.warning(f"Invalid power-on hours ({poh_hours}) for device {device.serial}. Cannot calculate workload.")
             return 0.0

        workload_tb_per_year = (total_bytes / (1024**4)) / poh_years
        logger.debug(f"Device {device.serial}: Total Bytes={total_bytes}, POH={poh_hours}, Workload={workload_tb_per_year:.2f} TB/year")
        return workload_tb_per_year