#
# Copyright (c) 2026 Circular Drive Initiative.
#
# This file is part of CDI Health.
# See https://github.com/circulardrives/cdi-grading-tool/ for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Mock Infrastructure for CDI Health Testing

Provides mock implementations of Smartctl and SG3Utils for testing
grading logic without real hardware.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cdi_health.classes.devices import Device


class MockDataLoader:
    """
    Loads and manages mock data from JSON files.
    """

    def __init__(self, mock_data_path: str | Path | None = None):
        """
        Initialize the mock data loader.

        :param mock_data_path: Path to mock data directory or file
        """
        self.mock_data_path = Path(mock_data_path) if mock_data_path else None
        self._cache: dict[str, dict] = {}

    def load_json_file(self, filepath: str | Path) -> dict:
        """
        Load a JSON file and return its contents.

        :param filepath: Path to JSON file
        :return: Parsed JSON data
        """
        filepath = Path(filepath)

        if filepath in self._cache:
            return self._cache[filepath]

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        self._cache[filepath] = data
        return data

    def get_device_data(self, device_id: str) -> dict | None:
        """
        Get mock data for a specific device ID.

        :param device_id: Device path like /dev/sda
        :return: Mock smartctl data or None
        """
        if self.mock_data_path is None:
            return None

        # If mock_data_path is a file, load it directly
        if self.mock_data_path.is_file():
            return self.load_json_file(self.mock_data_path)

        # If mock_data_path is a directory, try to find matching data
        # First check for exact device name match
        device_name = device_id.replace("/dev/", "")

        # Search in subdirectories
        for subdir in ["ata", "nvme", "scsi"]:
            subpath = self.mock_data_path / subdir
            if subpath.is_dir():
                for json_file in subpath.glob("*.json"):
                    data = self.load_json_file(json_file)
                    if data.get("device", {}).get("name") == device_id:
                        return data

        return None

    def get_all_device_data(self) -> list[dict]:
        """
        Get all mock device data from the mock data directory.

        :return: List of mock device data dictionaries
        """
        devices = []

        if self.mock_data_path is None:
            return devices

        # If mock_data_path is a file, load it directly
        if self.mock_data_path.is_file():
            return [self.load_json_file(self.mock_data_path)]

        # If mock_data_path is a directory, load all device files
        for subdir in ["ata", "nvme", "scsi"]:
            subpath = self.mock_data_path / subdir
            if subpath.is_dir():
                for json_file in sorted(subpath.glob("*.json")):
                    data = self.load_json_file(json_file)
                    devices.append(data)

        return devices

    def get_scan_results(self, scan_type: str = "mixed_devices") -> dict:
        """
        Get mock scan results.

        :param scan_type: Type of scan results (single_ata, mixed_devices, empty)
        :return: Mock scan results
        """
        if self.mock_data_path is None:
            return {"devices": []}

        # If mock_data_path is a file, create scan results from it
        if self.mock_data_path.is_file():
            data = self.load_json_file(self.mock_data_path)
            return {
                "json_format_version": [1, 0],
                "smartctl": data.get("smartctl", {}),
                "devices": [data.get("device", {})],
            }

        # Try to load scan results from scan_results directory
        scan_results_path = self.mock_data_path / "scan_results" / f"{scan_type}.json"
        if scan_results_path.is_file():
            return self.load_json_file(scan_results_path)

        # Generate scan results from available device files
        devices = []
        for subdir in ["ata", "nvme", "scsi"]:
            subpath = self.mock_data_path / subdir
            if subpath.is_dir():
                for json_file in sorted(subpath.glob("*.json")):
                    data = self.load_json_file(json_file)
                    if "device" in data:
                        devices.append(data["device"])

        return {
            "json_format_version": [1, 0],
            "smartctl": {
                "version": [7, 4],
                "exit_status": 0,
            },
            "devices": devices,
        }


class MockSmartctl:
    """
    Mock Smartctl class that returns pre-loaded JSON data.
    """

    def __init__(self, device_id: str = None, mock_data: dict = None):
        """
        Initialize mock Smartctl.

        :param device_id: Device path (e.g., /dev/sda)
        :param mock_data: Pre-loaded mock data dictionary
        """
        self.dut = device_id
        self._mock_data = mock_data or {}

        # Match real Smartctl interface
        self.acceptable_return_codes = [0, 4, 64, 192, 196, 216]
        self.bitmask_codes = {
            0: "Command line did not parse correctly",
            1: "Device open failed",
            2: "S.M.A.R.T command failed",
            3: "S.M.A.R.T Status returned 'DISK FAILING'",
            4: "S.M.A.R.T Status returned 'DISK OK' but found pre-fail attributes",
            5: "S.M.A.R.T Status returned 'DISK OK' but found usage attributes",
            6: "S.M.A.R.T Error Log contains errors",
            7: "S.M.A.R.T Self-test Log contains failed self-tests",
        }

    def get_all_as_json(self) -> dict | bool:
        """
        Get all device information as JSON (mock version).

        :return: Mock smartctl data dictionary
        """
        if self._mock_data:
            return self._mock_data
        return False

    def get_all_as_text(self) -> str | bool:
        """
        Get all device information as text (mock version).

        :return: Mock output as formatted text
        """
        if self._mock_data:
            return json.dumps(self._mock_data, indent=2)
        return False

    def get_health(self, as_json: bool = True):
        """
        Get device health (mock version).

        :return: Mock health command result
        """

        class MockCommand:
            def __init__(self, data):
                self._data = data

            def get_return_code(self):
                return self._data.get("smartctl", {}).get("exit_status", 0)

            def get_output(self):
                health = {"smart_status": self._data.get("smart_status", {})}
                return json.dumps(health).encode("utf-8")

        return MockCommand(self._mock_data)

    def get_version(self) -> str | bool:
        """
        Get smartctl version (mock version).
        """
        return "smartctl 7.4 (mock)"

    # Self-test methods (mock versions that do nothing)
    def abort_self_test(self):
        """Mock abort self-test."""
        return self._mock_command_result()

    def execute_self_test_offline(self, captive: bool = False, force: bool = False):
        """Mock offline self-test."""
        return self._mock_command_result()

    def execute_self_test_short(self, captive: bool = False, force: bool = False):
        """Mock short self-test."""
        return self._mock_command_result()

    def execute_self_test_long(self, captive: bool = False, force: bool = False):
        """Mock long self-test."""
        return self._mock_command_result()

    def execute_self_test_conveyance(self, captive: bool = False, force: bool = False):
        """Mock conveyance self-test."""
        return self._mock_command_result()

    def execute_self_test_selective(self, starting_lba=0, ending_lba=100, **kwargs):
        """Mock selective self-test."""
        return self._mock_command_result()

    def execute_self_test_vendor_specific(self, vendor_specific_command: str = "0x00", **kwargs):
        """Mock vendor-specific self-test."""
        return self._mock_command_result()

    def _mock_command_result(self):
        """Create a mock command result."""

        class MockCommand:
            def get_return_code(self):
                return 0

            def get_output(self):
                return b"{}"

            def has_errors(self):
                return False

        return MockCommand()


class MockSG3Utils:
    """
    Mock SG3Utils class for testing without real hardware.
    """

    def __init__(self, device_id: str, mock_sg_id: str = None):
        """
        Initialize mock SG3Utils.

        :param device_id: Device path (e.g., /dev/sda)
        :param mock_sg_id: Mock SCSI generic ID to return
        """
        self.dut = device_id
        self._mock_sg_id = mock_sg_id

    def sg_map26(self) -> str | bool:
        """
        Map block device to SCSI generic ID (mock version).

        :return: Mock SCSI generic ID or the device itself for NVMe
        """
        # For NVMe devices, return as-is (same as real implementation)
        if "/dev/nvme" in self.dut:
            return self.dut

        # Return mock SG ID if provided
        if self._mock_sg_id:
            return self._mock_sg_id

        # Generate a mock SG ID based on the device
        # e.g., /dev/sda -> /dev/sg0
        if self.dut.startswith("/dev/sd"):
            # Extract letter (sda -> a, sdb -> b, etc.)
            letter = self.dut[7:8]
            sg_num = ord(letter) - ord("a")
            return f"/dev/sg{sg_num}"

        return self.dut

    def test_unit_ready(self) -> str:
        """
        Test if device is ready (mock version).

        :return: Always returns "Ready" for mock
        """
        return "Ready"


class MockSeaTools:
    """
    Mock SeaTools class for testing without real hardware.
    """

    def __init__(self, device_id: str = None):
        """
        Initialize mock SeaTools.

        :param device_id: Device path
        """
        self.dut = device_id
        self.seachest_basics_path = "openSeaChest_Basics"
        self.seachest_smart_path = "openSeaChest_SMART"

    def get_all_as_text(self) -> str | bool:
        """
        Get all device info as text (mock version).

        :return: Mock SeaTools output
        """
        return f"Mock SeaTools output for {self.dut}"


def create_mock_device(
    json_file: str | Path = None,
    mock_data: dict = None,
    device_id: str = None,
) -> Device:
    """
    Create a Device instance using mock data instead of real hardware.

    :param json_file: Path to JSON file with mock smartctl data
    :param mock_data: Pre-loaded mock data dictionary
    :param device_id: Device ID to use (overrides data from file)
    :return: Device instance populated with mock data
    """
    # Import here to avoid circular imports
    from cdi_health.classes.devices import Device

    # Load data from file if provided
    if json_file:
        loader = MockDataLoader()
        mock_data = loader.load_json_file(json_file)

    if not mock_data:
        raise ValueError("Either json_file or mock_data must be provided")

    mock_data = json.loads(json.dumps(mock_data))
    nv_cli = mock_data.get("nvme_cli")
    if isinstance(nv_cli, dict) and isinstance(nv_cli.get("ocp_smart_log"), dict) and nv_cli["ocp_smart_log"]:
        if not mock_data.get("ocp_smart_log"):
            mock_data["ocp_smart_log"] = json.loads(json.dumps(nv_cli["ocp_smart_log"]))

    # Get device ID from data or use provided one
    if device_id is None:
        device_id = mock_data.get("device", {}).get("name", "/dev/mock0")

    # Create mock providers
    mock_smartctl = MockSmartctl(device_id=device_id, mock_data=mock_data)
    mock_sg3utils = MockSG3Utils(device_id=device_id)

    # Create device with mock providers
    device = Device.__new__(Device)

    # Initialize properties manually (bypass __init__)
    device.dut = device_id
    device.dut_sg = mock_sg3utils.sg_map26()
    device.state = mock_sg3utils.test_unit_ready()

    # Initialize all device properties with defaults
    _init_device_defaults(device)

    # Set tool instances
    device.seatools = MockSeaTools(device_id=device.dut_sg)
    device.smartctl = mock_smartctl

    # Initialize device using the mock data
    device.initialize()

    return device


def _init_device_defaults(device: Device) -> None:
    """
    Initialize device properties with default values.

    :param device: Device instance to initialize
    """
    device.wwn = "Not Reported"
    device.vendor = "Not Reported"
    device.model_number = "Not Reported"
    device.serial_number = "Not Reported"
    device.firmware_revision = "Not Reported"
    device.media_type = "Not Reported"
    device.transport_protocol = "Not Reported"
    device.transport_version = "Not Reported"
    device.transport_revision = "Not Reported"
    device.rotation_rate = "Not Reported"
    device.form_factor = "Not Reported"
    device.power_on_hours = "Not Reported"
    device.size = 0
    device.bytes = 0
    device.kilobytes = 0.0
    device.megabytes = 0.0
    device.gigabytes = 0.0
    device.terabytes = 0.0
    device.kibibytes = 0.0
    device.mebibytes = 0.0
    device.gibibytes = 0.0
    device.tebibytes = 0.0
    device.sectors = 0
    device.logical_sector_size = 0
    device.physical_sector_size = 0

    # NVMe Namespaces
    device.nvme_namespaces = None

    # S.M.A.R.T
    device.smart_supported = False
    device.smart_enabled = False
    device.smart_status = False
    device.smart_attributes = None
    device.smart_self_tests = None
    device.smart_self_tests_supported = False
    device.smart_self_tests_conveyance_supported = False
    device.smart_self_tests_selective_supported = False
    device.smart_short_self_test_duration = None
    device.smart_long_self_test_duration = None
    device.smart_conveyance_self_test_duration = None

    # Security Support
    device.security_supported = False
    device.security_enabled = False
    device.security_locked = False
    device.security_frozen = False

    # Secure Erase Support
    device.secure_erase_supported = False
    device.enhanced_secure_erase_supported = None
    device.secure_erase_duration = False
    device.enhanced_secure_erase_duration = None

    # Sanitize Support
    device.sanitize_supported = False
    device.sanitize_block_erase_supported = False
    device.sanitize_cryptographic_erase_supported = False
    device.sanitize_overwrite_erase_supported = False
    device.sanitize_exit_failure_mode_supported = False

    # Format Unit Support
    device.scsi_format_unit_supported = False
    device.nvme_format_unit_supported = False
    device.nvme_format_unit_cryptographic_erase_supported = False
    device.nvme_format_unit_user_data_erase_supported = False

    # NIST/IEEE Support
    device.can_nist_clear = False
    device.can_nist_purge = False
    device.can_ieee_clear = False
    device.can_ieee_purge = False

    # Estimated Erasure Duration
    device.estimated_erasure_duration = None

    # CDI Grading
    device.cdi_eligible = False
    device.cdi_certified = False
    device.cdi_grade = "U"

    # Generic Attributes
    device.pending_sectors = None
    device.reallocated_sectors = None
    device.reallocated_event_count = None
    device.uncorrectable_errors = None

    # Counters
    device.start_stop_count = None
    device.power_cycle_count = None
    device.load_cycle_count = None

    # SSD Attributes
    device.ssd_percentage_used_endurance = None
    device.ssd_media_wearout_indicator = None
    device.ssd_wear_levelling = None
    device.ssd_life_left = None

    # Temperatures
    device.current_temperature = None
    device.maximum_temperature = None
    device.minimum_temperature = None
    device.highest_temperature = None
    device.lowest_temperature = None
    device.average_short_temperature = None
    device.average_long_temperature = None
    device.highest_average_short_temperature = None
    device.lowest_average_short_temperature = None
    device.highest_average_long_temperature = None
    device.lowest_average_long_temperature = None
    device.time_over_temperature = None
    device.temperature_log = None

    # Outputs and Flags
    device.outputs = {}
    device.flags = []

    # Smartctl JSON
    device.smartctl_json = None


class MockDevices:
    """
    Mock Devices class for loading multiple mock devices.
    """

    def __init__(
        self,
        mock_data_path: str | Path = None,
        ignore_ata: bool = False,
        ignore_nvme: bool = False,
        ignore_scsi: bool = False,
    ):
        """
        Initialize mock Devices.

        :param mock_data_path: Path to mock data directory or file
        :param ignore_ata: Skip ATA devices
        :param ignore_nvme: Skip NVMe devices
        :param ignore_scsi: Skip SCSI devices
        """
        self.mock_data_path = Path(mock_data_path) if mock_data_path else None
        self.ignore_ata = ignore_ata
        self.ignore_nvme = ignore_nvme
        self.ignore_scsi = ignore_scsi

        # Lists
        self.scanned: list = []
        self.devices: list = []
        self.failures: list = []

        # Protocols
        self.ata_devices: list = []
        self.nvme_devices: list = []
        self.scsi_devices: list = []

        # Load and analyze mock devices
        self._load_mock_devices()

    def _load_mock_devices(self) -> None:
        """Load mock devices from the mock data path."""
        if self.mock_data_path is None:
            return

        loader = MockDataLoader(self.mock_data_path)

        # Get all device data
        all_data = loader.get_all_device_data()

        for data in all_data:
            device_info = data.get("device", {})
            protocol = device_info.get("protocol", "Unknown")

            # Filter by protocol
            if protocol == "ATA" and self.ignore_ata:
                continue
            if protocol == "NVMe" and self.ignore_nvme:
                continue
            if protocol == "SCSI" and self.ignore_scsi:
                continue

            # Track scanned devices
            self.scanned.append(device_info)

            # Track by protocol
            if protocol == "ATA":
                self.ata_devices.append(device_info)
            elif protocol == "NVMe":
                self.nvme_devices.append(device_info)
            elif protocol == "SCSI":
                self.scsi_devices.append(device_info)

            # Create mock device
            try:
                device = create_mock_device(mock_data=data)
                self.devices.append(device.to_dict(pop=True))
            except Exception as e:
                self.failures.append({"device": device_info, "error": str(e)})

    @property
    def get_total_devices(self) -> int:
        """Get total number of devices."""
        return len(self.devices)

    @property
    def are_ready(self) -> bool:
        """Check if all devices are ready."""
        return all(d.get("state") == "Ready" for d in self.devices)

    @property
    def are_hdds(self) -> bool:
        """Check if all devices are HDDs."""
        return all(d.get("media_type") == "HDD" for d in self.devices)

    @property
    def are_ssds(self) -> bool:
        """Check if all devices are SSDs."""
        return all(d.get("media_type") == "SSD" for d in self.devices)

    @property
    def are_nvme(self) -> bool:
        """Check if all devices are NVMe."""
        return all(d.get("transport_protocol") == "NVMe" for d in self.devices)
