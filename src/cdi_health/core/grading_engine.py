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

    def _get_smart_attribute(self, smart_data: dict, attr_id: int, attr_name: str | None = None) -> Optional[dict]:
        """Safely retrieve a specific SMART attribute by ID or name."""
        if not smart_data or "ata_smart_attributes" not in smart_data:
            return None

        attributes = smart_data["ata_smart_attributes"].get("table", [])
        for attr in attributes:
            if attr.get("id") == attr_id:
                return attr
            # Fallback to checking name if provided and ID doesn't match
            if attr_name and attr.get("name") == attr_name:
                 return attr
        return None

    def _get_attribute_raw_value(self, attribute: Optional[dict]) -> int:
        """Safely get the raw value from a SMART attribute dictionary."""
        if attribute and "raw" in attribute and "value" in attribute["raw"]:
            try:
                return int(attribute["raw"]["value"])
            except (ValueError, TypeError):
                return 0
        return 0

    def _get_attribute_value(self, attribute: Optional[dict]) -> int:
        """Safely get the normalized value from a SMART attribute dictionary."""
        if attribute and "value" in attribute:
            try:
                return int(attribute["value"])
            except (ValueError, TypeError):
                 # Default to 100 if conversion fails, common for 'normalized' values
                 # where higher is better and max is often 100 or 200/253.
                return 100
        return 100 # Default if attribute is None or value missing

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

        # Check pending sectors (ID 197)
        pending_sectors_attr = self._get_smart_attribute(device.smart_data, 197, "Current_Pending_Sector")
        pending_sectors_count = self._get_attribute_raw_value(pending_sectors_attr)
        if pending_sectors_count > self.PENDING_SECTORS_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.PENDING_SECTORS,
            )

        # Check reallocated sectors (ID 5)
        reallocated_sectors_attr = self._get_smart_attribute(device.smart_data, 5, "Reallocated_Sector_Ct")
        reallocated_sectors_count = self._get_attribute_raw_value(reallocated_sectors_attr)
        if reallocated_sectors_count > self.REALLOCATED_SECTORS_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.REALLOCATED_SECTORS,
            )

        # Check percentage used (for SSDs, ID 231 or 233 - check PRD for exact ID/logic)
        # Example using ID 233 (Media_Wearout_Indicator) raw value, assuming higher is worse
        # OR ID 177 (Wear_Leveling_Count) normalized value, lower is worse? -> Consult PRD!
        # For now, let's check ID 231 'SSD Life Left' or similar common names
        percent_used_attr = self._get_smart_attribute(device.smart_data, 231, "SSD_Life_Left")
        # Assuming normalized value where 100 is new, 0 is worn out.
        life_left_value = self._get_attribute_value(percent_used_attr)
        percentage_used = 100 - life_left_value # Estimate percentage used

        # Fallback check using common name if ID 231 not found
        if percent_used_attr is None:
            percent_used_attr_alt = self._get_smart_attribute(device.smart_data, -1, "Percent_Lifetime_Used") # No standard ID, use name
            percentage_used = self._get_attribute_raw_value(percent_used_attr_alt) # Raw value often used here

        if percentage_used > self.PERCENT_USED_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.PERCENT_USED,
            )

        # Check available spare (for SSDs, ID 173 or similar - check PRD)
        # Example using ID 173 'Erase_Fail_Count' or 'Available_Reservd_Space' normalized value
        available_spare_attr = self._get_smart_attribute(device.smart_data, 173, "Available_Reservd_Space")
        available_spare_value = self._get_attribute_value(available_spare_attr) # Normalized value, lower is worse
        if available_spare_value <= self.AVAILABLE_SPARE_THRESHOLD:
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