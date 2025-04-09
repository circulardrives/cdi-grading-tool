"""
Core functionality for the CDI Health tool.

This package contains the core components for device management, grading, and reporting.
"""

from cdi_health.core.device_manager import DeviceManager, StorageDevice, TransportProtocol
from cdi_health.core.grading_engine import GradingEngine, GradedDevice, DeviceStatus, FlagReason, FailureReason
from cdi_health.core.report_generator import ReportGenerator

__all__ = [
    "DeviceManager",
    "StorageDevice",
    "TransportProtocol",
    "GradingEngine",
    "GradedDevice",
    "DeviceStatus",
    "FlagReason",
    "FailureReason",
    "ReportGenerator",
]