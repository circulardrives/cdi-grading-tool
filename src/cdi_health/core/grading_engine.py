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
        # Check pending sectors
        if device.smart_data.get("pending_sectors", 0) > self.PENDING_SECTORS_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.PENDING_SECTORS,
            )

        # Check reallocated sectors
        if device.smart_data.get("reallocated_sectors", 0) > self.REALLOCATED_SECTORS_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.REALLOCATED_SECTORS,
            )

        # Check percentage used (for SSDs)
        if device.smart_data.get("percentage_used", 0) > self.PERCENT_USED_THRESHOLD:
            return GradedDevice(
                device=device,
                status=DeviceStatus.FAIL,
                failure_reason=FailureReason.PERCENT_USED,
            )

        # Check available spare (for SSDs)
        if device.smart_data.get("available_spare", 100) <= self.AVAILABLE_SPARE_THRESHOLD:
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
        # Get host read/write data
        host_reads = device.smart_data.get("host_reads_bytes", 0) or device.nvme_data.get("host_reads_bytes", 0)
        host_writes = device.smart_data.get("host_writes_bytes", 0) or device.nvme_data.get("host_writes_bytes", 0)
        total_bytes = host_reads + host_writes

        # Get power-on hours
        poh_hours = device.smart_data.get("power_on_hours", 0) or device.nvme_data.get("power_on_hours", 0)
        if not poh_hours:
            return 0.0

        # Convert to TB/year
        poh_years = poh_hours / (24 * 365)
        if not poh_years:
            return 0.0

        return (total_bytes / (1024**4)) / poh_years  # Convert bytes to TB and divide by years