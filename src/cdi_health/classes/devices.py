#
# Copyright (c) 2025 Circular Drive Initiative.
#
# This file is part of CDI Health.
# See https://github.com/circulardrives/cdi-grading-tool-alpha/ for further info.
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
Circular Drive Initiative - Devices Class

@language    Python 3.12
@framework   PySide 6
@version     0.0.1
"""

from __future__ import annotations

# Modules
import json

# Concurrent Futures
from concurrent.futures import ThreadPoolExecutor

# Data Classes
from dataclasses import dataclass

# Exceptions
from cdi_health.classes.exceptions import CommandException, DevicesException

# Helpers
from cdi_health.classes.helpers import Helper

# Tools
from cdi_health.classes.tools import Command, SeaTools, SG3Utils, Smartctl

# Constants
from cdi_health.constants import (
    CDI_MAXIMUM_PENDING_SECTORS,
    CDI_MAXIMUM_REALLOCATED_SECTORS,
    CDI_MAXIMUM_UNCORRECTABLE_ERRORS,
    known_brands_list,
    none,
)


class Device:
    """
    Device Class
    """

    # Protocol Map
    protocol_map = {
        "ATA": "ATA",
        "FusionIO": "FusionIO",
        "NVMe": "NVMe",
        "SCSI": "SCSI",
        "SD": "SD",
        "USB": "USB",
    }

    # Rotation Rate Map
    rotation_rate_map = {
        0: "SSD",
        5400: "HDD",
        5700: "HDD",
        7200: "HDD",
        10000: "HDD",
        15030: "HDD",
        10500: "HDD",
        15000: "HDD",
        "Not Reported": "Not Reported",
    }

    # Grading Map - TODO - Complete a grading mapping and create loop?
    grading_map = {
        "smart": {
            "equality": "==",
            "value": "Pass",
        },
        "smart_self_test": {
            "equality": "==",
            "value": "Pass",
        },
        "smart_conveyance_self_test": {
            "equality": "==",
            "value": "Pass",
        },
        "health": {
            "equality": ">=",
            "value": 80,
        },
        "reallocated_sectors": {
            "equality": "<=",
            "value": 50,
        },
    }

    def __init__(self, device_id: str = None):
        """
        Constructor
        :param device_id: Device ID ("/dev/sda")
        """

        # Properties
        self.dut: str = device_id
        self.dut_sg: str = SG3Utils(self.dut).sg_map26()
        self.state: str = SG3Utils(self.dut_sg).test_unit_ready()
        self.wwn: str = "Not Reported"
        self.vendor: str = "Not Reported"
        self.model_number: str = "Not Reported"
        self.serial_number: str = "Not Reported"
        self.firmware_revision: str = "Not Reported"
        self.media_type: str = "Not Reported"
        self.transport_protocol: str = "Not Reported"
        self.transport_version: str = "Not Reported"
        self.transport_revision: str = "Not Reported"
        self.rotation_rate: str = "Not Reported"
        self.form_factor: str = "Not Reported"
        self.power_on_hours: str = "Not Reported"
        self.power_on_time: str = "Not Reported"
        self.temperature: str = "Not Reported"
        self.lifetime_remaining: str = "Not Reported"
        self.description: str = "Not Reported"
        self.tip: str = "Not Reported"

        # Capacity
        self.size = None
        self.bytes = None
        self.kilobytes = None
        self.megabytes = None
        self.gigabytes = None
        self.terabytes = None
        self.kibibytes = None
        self.mebibytes = None
        self.gibibytes = None
        self.tebibytes = None

        # Sectors
        self.sectors = None
        self.logical_sector_size = None
        self.physical_sector_size = None
        self.native_maximum_sectors = None
        self.current_maximum_sectors = None

        # Namespaces
        self.namespaces = None

        # S.M.A.R.T
        self.smart_supported = False
        self.smart_enabled = False
        self.smart_status = False
        self.smart_attributes = None
        self.smart_self_tests = None
        self.smart_self_tests_supported = False
        self.smart_self_tests_conveyance_supported = False
        self.smart_self_tests_selective_supported = False
        self.smart_short_self_test_duration = None
        self.smart_long_self_test_duration = None
        self.smart_conveyance_self_test_duration = None

        # TCG Support
        self.tcg_supported = False
        self.tcg_enabled = False
        self.tcg_locked = False
        self.tcg_enterprise = False
        self.tcg_ruby = False
        self.tcg_opal = False
        self.tcg_opalite = False
        self.tcg_pyrite = False

        # Security Support
        self.security_supported = False
        self.security_enabled = False
        self.security_locked = False
        self.security_frozen = False

        # Secure Erase Support
        self.secure_erase_supported = False
        self.enhanced_secure_erase_supported = None

        # Secure Erase Duration
        self.secure_erase_duration = False
        self.enhanced_secure_erase_duration = None

        # Sanitize Support
        self.sanitize_supported = False
        self.sanitize_block_erase_supported = False
        self.sanitize_cryptographic_erase_supported = False
        self.sanitize_overwrite_erase_supported = False
        self.sanitize_exit_failure_mode_supported = False

        # SCSI Format Unit Support
        self.scsi_format_unit_supported = False

        # NVMe Format Unit Support
        self.nvme_format_unit_supported = False
        self.nvme_format_unit_cryptographic_erase_supported = False
        self.nvme_format_unit_user_data_erase_supported = False

        # NIST/IEEE Support
        self.can_nist_clear = False
        self.can_nist_purge = False
        self.can_ieee_clear = False
        self.can_ieee_purge = False

        # Estimated Erasure Duration
        self.estimated_erasure_duration = None

        # CDI Grading
        self.cdi_eligible = False  # Defaults to False until eligible
        self.cdi_certified = False  # Defaults to False until certified
        self.cdi_grade = "U"  # Defaults to "U" which means "Ungraded"

        # Generic Attributes
        self.pending_sectors = None
        self.reallocated_sectors = None
        self.reallocated_event_count = None
        self.uncorrectable_errors = None

        # Counters
        self.start_stop_count = None
        self.power_cycle_count = None
        self.load_cycle_count = None

        # SSD Attributes
        self.ssd_percentage_used_endurance = None
        self.ssd_media_wearout_indicator = None
        self.ssd_wear_levelling = None
        self.ssd_life_left = None

        # Temperatures
        self.current_temperature = None
        self.maximum_temperature = None
        self.minimum_temperature = None
        self.highest_temperature = None
        self.lowest_temperature = None
        self.average_short_temperature = None
        self.average_long_temperature = None
        self.highest_average_short_temperature = None
        self.lowest_average_short_temperature = None
        self.highest_average_long_temperature = None
        self.lowest_average_long_temperature = None
        self.time_over_temperature = None

        # Temperature Log
        self.temperature_log = None

        # Hidden Areas
        self.amac_supported = False
        self.amac_enabled = False
        self.hpa_supported = False
        self.hpa_enabled = False
        self.dco_supported = False
        self.dco_enabled = False

        # Zoned Device Support
        self.zoned_supported = False
        self.zoned_enabled = False

        # Supported Specifications
        self.supported_specifications = None
        self.supported_features = None

        # Outputs
        self.outputs = dict()

        # Flags
        self.flags = list()

        # Tools
        self.seatools = SeaTools(device_id=self.dut_sg)
        self.smartctl = Smartctl(device_id=self.dut_sg)

        # TODO - Add more tools? Remove tools? Do we only want Smartctl and Seatools for now?
        # TODO - sg3-utils, nvme-cli, sedutil-cli

        # Outputs
        self.smartctl_json = None

        # Initialize Device
        self.initialize()

    def to_dict(self, redacted=False, pop=False):
        """
        To Dictionary
        @return:
        """

        # Attributes to Modify
        attributes_to_modify = [
            "smartctl",
            "seatools",
            "sgutils",
        ]

        # Object Copy
        obj_dict = self.__dict__.copy()

        # Modify Attributes
        if redacted:
            # For Attribute in Attributes to Modify
            for attr in attributes_to_modify:
                # If Attribute in Dict
                if attr in obj_dict:
                    # Amend to Redacted
                    obj_dict[attr] = "<redacted>"

            # Return Copy
            return obj_dict

        # If Pop Attribute
        if pop:
            # For Attribute in Attributes to Modify
            for attr in attributes_to_modify:
                # If Attribute in Dict
                if attr in obj_dict:
                    # Amend to Popped
                    del obj_dict[attr]

            # Return Copy
            return obj_dict

        return obj_dict

    def initialize(self) -> None:
        """
        Initialize the Device
        :return: None
        """

        # Collect Smartctl Information as JSON
        self.smartctl_json = self.smartctl.get_all_as_json()

        # Check Transport Protocol - ! MUST BE BEFORE MEDIA !
        self.transport_protocol = self.determine_transport_protocol

        # Check Media Type - ! MUST BE AFTER TRANSPORT !
        self.media_type = self.determine_media_type

        # If ATA
        if self.is_ata:
            # Collect ATA Information
            ATAProtocol(device=self, smartctl=self.smartctl_json)

        # If NVMe
        if self.is_nvme:
            # Collect NVMe Information
            NVMeProtocol(device=self, smartctl=self.smartctl_json)

        # If SCSI
        if self.is_scsi:
            # Collect SCSI Information
            SCSIProtocol(device=self, smartctl=self.smartctl_json)

        # If USB
        if self.is_usb:
            # Collect USB Information
            USBProtocol(device=self)

    def refresh(self):
        """
        Refresh Device
        """

        # Reset Output
        self.outputs = dict()

        # Reset Flags
        self.flags = list()

        # Initialize
        self.initialize()

    """ Helpers """

    @staticmethod
    def determine_brand_by_model_number(model: str) -> str | None:
        """
        Check Brand on Model
        :param model: the model number of the device
        :return: a brand if it exists
        """

        # Loop Brands
        for brand in known_brands_list:
            # If Brand equals Model
            if brand in model:
                # Return Brand
                return brand

        # Return
        return None

    @staticmethod
    def determine_brand_by_model_number_starts_with(model) -> str | None:
        """
        Check Brand on Model Starts with
        :param model: the model number of the device
        :return: a brand if it exists
        Todo - Add more known Model Numbers that start with XXX - helps with ATA devices that don't share a Vendor in the Model Number
        Todo - See known_brands_list in constants.py
        """

        """
        HPE Devices
        """

        # HPE List
        hpe_list = [
            "MB",
            "MK",
            "MM",
        ]

        # Loop HPE prefixes
        for prefix in hpe_list:
            # If Starts with Prefix and has 3 Digits after the first two letters...
            if model.startswith(prefix) and len(model) >= 5 and model[2:5].isdigit():
                # Return HPE
                return "HPE"

        """
        HGST/Hitachi Devices
        """

        # HGST List
        hgst_devices = [
            "HUS",
        ]

        for prefix in hgst_devices:
            if model.startswith(prefix) and len(model) >= 5 and model[2:5].isdigit():
                return "HGST"

        """
        Intel Devices
        """

        # Intel List
        intel_devices = [
            "SSDS",
        ]

        # Loop
        for prefix in intel_devices:
            if model.startswith(prefix):
                return "Intel"

        """
        Samsung Devices
        """

        # Samsung List
        samsung_devices = [
            "MZ-",
            "MZ7",
            "MZ7K",
        ]

        # Loop
        for prefix in samsung_devices:
            if model.startswith(prefix):
                return "Samsung"

        """
        Seagate Devices
        """

        # Seagate List
        seagate_devices = [
            "ST",
            "ST500",
        ]

        # Loop
        for prefix in seagate_devices:
            if model.startswith(prefix):
                return "Seagate"

        """
        Toshiba Devices
        """

        # Toshiba List
        toshiba_devices = [
            "THN",
        ]

        for prefix in toshiba_devices:
            if model.startswith(prefix) and len(model) >= 5 and model[2:5].isdigit():
                return "Toshiba"

        """
        Western Digital Devices
        """

        # Western Digital List
        wdc_devices = [
            "WDC-",
        ]

        for prefix in wdc_devices:
            if model.startswith(prefix) and len(model) >= 5 and model[2:5].isdigit():
                return "Western Digital"

        # No match, return None
        return None

    @staticmethod
    def determine_model_by_model_number(model) -> str:
        """
        Check Model on Model
        :param model: the model number of the device
        :return: a model number stripped of its brand if it exists
        """

        # Loop Brands
        for brand in known_brands_list:
            # If Brand in Model Number
            if brand in model:
                # Return Model Number with the Brand removed
                return model.replace(f"{brand} ", "")

        # Return Model as is
        return model

    """ Type Properties """

    @property
    def determine_media_type(self) -> str:
        """
        Determine the Media Type
        :return: Media Type
        """

        # Check Rotation Rate
        if "rotation_rate" in self.smartctl_json:
            # Set Media Type
            return self.rotation_rate_map.get(
                # Get Rotation Rate
                self.smartctl_json.get("rotation_rate", "Not Reported"),
                # Fallback
                "Not Reported",
            )
        else:
            # If Transport Protocol is NVMe
            if self.transport_protocol == "NVMe":
                # Set Media Type to SSD
                return "SSD"
            # If Transport Protocol is ATA
            elif self.transport_protocol == "ATA":
                # Set Media Type to HDD
                return "HDD"

    @property
    def determine_transport_protocol(self) -> str:
        """
        Determine the Transport Protocol
        :return: the Transport Protocol
        """

        # Return Transport Protocol
        return self.protocol_map.get(
            # Get Transport Protocol
            self.smartctl_json["device"]["protocol"],
            # Fallback
            "Unknown",
        )

    """ Is Properties"""

    @property
    def is_ready(self) -> bool:
        """
        Determines if Device is Ready via Test Unit Ready Command
        :return: True if ready, False otherwise
        """

        return True

    @property
    def is_mounted(self) -> bool:
        """
        Determines if Device is mounted
        :return: True if mounted, False otherwise
        """

        return True

    @property
    def is_hdd(self) -> bool:
        """
        Determines if Device is HDD
        :return: True if HDD, False otherwise
        """

        # If Media Type is HDD
        if self.media_type == "HDD":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_ssd(self) -> bool:
        """
        Determines if Device is SSD
        :return:
        """

        # If Media Type is SSD
        if self.media_type == "SSD":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_ata(self) -> bool:
        """
        Determines if Device is ATA
        :return:
        """

        # If Transport Protocol is ATA
        if self.transport_protocol == "ATA":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_nvme(self) -> bool:
        """
        Determines if Device is NVMe
        :return:
        """

        # If Transport Protocol is NVMe
        if self.transport_protocol == "NVMe":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_scsi(self) -> bool:
        """
        Determines if Device is SCSI
        :return:
        """

        # If Transport Protocol is SCSI
        if self.transport_protocol == "SCSI":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_usb(self) -> bool:
        """
        Determines if Device is SCSI
        :return:
        """

        # If Transport Protocol is USB
        if self.transport_protocol == "USB":
            # Return True
            return True

        # Return False
        return False

    """ Grading Methods """

    def determine_grade(self):
        pass

    @property
    def is_grade_a(self) -> bool:
        """
        Determines if the device is CDI grade A
        :return:
        """

        # If CDI Grade is A
        if self.cdi_grade == "A":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_grade_b(self) -> bool:
        """
        Determines if the device is CDI grade B
        :return:
        """

        # If CDI Grade is A
        if self.cdi_grade == "B":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_grade_c(self) -> bool:
        """
        Determines if the device is CDI grade C
        :return:
        """

        # If CDI Grade is A
        if self.cdi_grade == "C":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_grade_d(self) -> bool:
        """
        Determines if the device is CDI grade C
        :return:
        """

        # If CDI Grade is A
        if self.cdi_grade == "D":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_grade_f(self) -> bool:
        """
        Determines if the device is CDI grade F
        :return:
        """

        # If CDI Grade is A
        if self.cdi_grade == "F":
            # Return True
            return True

        # Return False
        return False

    @property
    def is_certified_for_reuse(self) -> bool:
        """
        Determines if certified for reuse against CDI standard
        :return:
        """

        # If CDI Grade is Certified
        if self.cdi_certified:
            # Return True
            return True

        # Return False
        return False

    """ Information Commands """

    def execute_identify_command(self):
        """
        Execute Identify
        :return: Command if OK | bool (False) if Fail
        """

        # Try
        try:
            # Execute S.M.A.R.T Health Test
            return self.smartctl.get_health()

        # If Command Exception
        except CommandException:
            # Return False
            return False

    def execute_smart_health_test(self):
        """
        Execute S.M.A.R.T Health Test
        :return: Command if OK | bool (False) if Fail
        :version: 1.0:
        """

        # Try
        try:
            # Execute S.M.A.R.T Health Test
            return self.smartctl.get_health()

        # If Command Exception
        except CommandException:
            # Return False
            return False

    """ Self-Test Commands """

    def execute_smart_short_self_test(
        self,
        captive: bool = False,
        use_smartctl: bool = True,
        use_seatools: bool = False,
    ) -> Command | bool:
        """
        Execute a Firmware-based S.M.A.R.T Short Self-test
        :param captive: execute self-test in Captive mode
        :param use_smartctl: use Smartctl (defaults to True)
        :param use_seatools: use SeaTools instead of Smartctl (defaults to False)
        :return: Command if OK | bool (False) if Fail
        :version: 1.0:
        """

        # Try
        try:
            # If Smartctl
            if use_smartctl:
                # Execute Short Self-test
                return self.smartctl.execute_self_test_short(captive=captive)

            # If SeaTools
            if use_seatools:
                # Execute Short Self-test
                # TODO - write seatools self-test logic and handler
                return self.smartctl.execute_self_test_short(captive=captive)

        # If Command Exception
        except CommandException:
            # Return False
            return False

    def execute_smart_long_self_test(
        self,
        captive: bool = False,
        use_smartctl: bool = True,
        use_seatools: bool = False,
    ) -> Command | bool:
        """
        Execute a Firmware-based S.M.A.R.T Extended Self-test
        :param captive: execute self-test in Captive mode
        :param use_smartctl: use Smartctl (defaults to True)
        :param use_seatools: use SeaTools instead of Smartctl (defaults to False)
        :return: Command if OK | bool (False) if Fail
        :version: 1.0:
        """

        # Try
        try:
            # If Smartctl
            if use_smartctl:
                # Execute Short Self-test
                return self.smartctl.execute_self_test_long(captive=captive)

            # If SeaTools
            if use_seatools:
                # Execute Short Self-test
                # TODO - write seatools self-test logic and handler
                return self.smartctl.execute_self_test_long(captive=captive)

        # If Command Exception
        except CommandException:
            # Return False
            return False

    def execute_smart_conveyance_self_test(
        self,
        captive: bool = False,
        use_smartctl: bool = True,
        use_seatools: bool = False,
    ) -> Command | bool:
        """
        Execute a Firmware-based S.M.A.R.T Conveyance Self-test
        :param captive: execute self-test in Captive mode
        :param use_smartctl: use Smartctl (defaults to True)
        :param use_seatools: use SeaTools instead of Smartctl (defaults to False)
        :return: Command if OK | bool (False) if Fail
        :version: 1.0
        """

        # Try
        try:
            # If Smartctl
            if use_smartctl:
                # Execute Conveyance Self-test
                return self.smartctl.execute_self_test_conveyance(captive=captive)

            # If SeaTools
            if use_seatools:
                # Execute Conveyance Self-test
                # TODO - write seatools self-test logic and handler
                return self.smartctl.execute_self_test_conveyance(captive=captive)

        # If Command Exception
        except CommandException:
            # Return False
            return False

    def execute_smart_vendor_self_test(
        self,
        vendor_specific_command: str = "0x00",
        captive: bool = False,
        use_smartctl: bool = True,
        use_seatools: bool = False,
    ) -> Command | bool:
        """
        Execute a Firmware-based S.M.A.R.T Vendor-specific Self-test
        :param vendor_specific_command: the vendor-specific command code
        :param captive: execute self-test in Captive mode
        :param use_smartctl: use Smartctl (defaults to True)
        :param use_seatools: use SeaTools instead of Smartctl (defaults to False)
        :return: Command if OK | bool (False) if Fail
        :version: 1.0:
        """

        # Try
        try:
            # If Smartctl
            if use_smartctl:
                # Execute Short Self-test
                return self.smartctl.execute_self_test_vendor_specific(
                    vendor_specific_command=vendor_specific_command,
                    captive=captive,
                )

            # If SeaTools
            if use_seatools:
                # Execute Short Self-test
                return self.smartctl.execute_self_test_vendor_specific(
                    vendor_specific_command=vendor_specific_command,
                    captive=captive,
                )  # TODO - write seatools self-test logic and handler

        # If Command Exception
        except CommandException:
            # Return False
            return False


class Devices:
    """
    Devices Class
    """

    # Commands
    scan_devices_command: str = "smartctl --scan-open -j"
    scan_devices_alt_command: str = "lsblk -d -b -e 1,7,11,252 -O -J"

    def __init__(
        self,
        ignore_ata: bool = False,
        ignore_nvme: bool = False,
        ignore_scsi: bool = False,
        ignore_removable: bool = False,
    ):
        """
        Constructor
        """

        # Lists
        self.scanned: list = list()
        self.devices: list = list()
        self.failures: list = list()

        # Protocols
        self.ata_devices: list = list()
        self.nvme_devices: list = list()
        self.scsi_devices: list = list()
        self.removable_devices: list = list()

        # Prepare Command
        self.scan_command = Command(command=self.scan_devices_command)

        # Try
        try:
            # Determine Ignorance
            self.ignore_ata: bool = ignore_ata
            self.ignore_nvme: bool = ignore_nvme
            self.ignore_scsi: bool = ignore_scsi
            self.ignore_removable: bool = ignore_removable

            # Scan Devices
            self.scan_devices()

            # Analyse Devices
            self.analyse_devices()

        # If Exception
        except CommandException as exception:
            # Raise Device Exception
            raise DevicesException(f"An error occurred initializing Devices: Command Exception = {exception}")

    def __repr__(self):
        """
        Representation String
        :return:
        """

        # Return
        return f"Devices({self.devices})"

    def scan_devices(self) -> bool:
        """
        Scan for Devices
        :return: bool
        """

        # Run Command
        self.scan_command.run()

        # If Return Code is not 0
        if self.scan_command.get_return_code() != 0:
            # If Command has Errors
            if self.scan_command.has_errors():
                # Raise Exception
                raise CommandException(self.scan_command)

            # Raise Exception
            raise CommandException(self.scan_command)

        # Decode JSON
        json_output = json.loads(self.scan_command.get_output())

        # Loop Devices
        for device in json_output["devices"]:
            # If Open Error in Drive
            if "open_error" in device:
                # Append to Failure List
                self.failures.append(device)

                # Continue
                continue

            # If MegaRAID Bus
            if device["name"].startswith("/dev/bus"):
                # Continue - TODO - provide handler for MegaRAID volumes? No?
                continue

            # Get Type
            device_type = device["protocol"]

            # If Device Type is ATA and Ignore is True, skip the device
            if device_type == "ATA" and self.ignore_ata:
                continue

            # If Device Type is NVMe and Ignore is True, skip the device
            elif device_type == "NVMe" and self.ignore_nvme:
                continue

            # If Device Type is SCSI and Ignore is True, skip the device
            elif device_type == "SCSI" and self.ignore_scsi:
                continue

            # If ATA
            if device_type == "ATA":
                # Append ATA Device
                self.ata_devices.append(device)

            # If NVMe
            elif device_type == "NVMe":
                # Append NVMe Device
                self.nvme_devices.append(device)

            # If SCSI
            elif device_type == "SCSI":
                # Append SCSI device
                self.scsi_devices.append(device)

            # Append Scanned Device
            self.scanned.append(device)

        # Return
        return True

    def analyse_devices(self) -> bool:
        """
        Analyse Devices
        :return: bool
        """

        # Reset Devices
        self.devices = list()

        # Create Threads and Analyse Devices
        with ThreadPoolExecutor() as analysis:
            # Devices List
            self.devices = list(
                # Map List Comprehension
                analysis.map(self.analyse_device, [drive["name"] for drive in self.scanned])
            )

        # Return
        return True

    @staticmethod
    def analyse_device(device_id: str):
        """
        Analyse Device
        :param device_id: Device ID
        :return: a Device instance
        """

        # Try
        try:
            # Get Device
            device = Device(device_id=device_id).to_dict(pop=True)

        # If CommandException
        except CommandException:
            # False
            return False

        # Get Drive
        return device

    @property
    def get_devices(self) -> list:
        """
        Get Devices
        :return: list of Devices
        """

        # Return Devices
        return self.devices

    @property
    def get_ata_devices(self) -> list:
        """
        Get ATA Devices
        :return: list of ATA Devices
        """

        # Return Devices
        return self.devices

    @property
    def get_ide_devices(self):
        """
        Get IDE Devices
        :return: list of IDE Devices
        """

        # Return Devices
        return self.devices

    @property
    def get_nvme_devices(self):
        """
        Get NVMe Devices
        :return: list of NVMe Devices
        """

        # Return Devices
        return self.devices

    @property
    def get_scsi_devices(self):
        """
        Get SCSI Devices
        :return: list of SCSI Devices
        """

        # Return Devices
        return self.devices

    @property
    def get_usb_devices(self):
        """
        Get USB Devices
        :return: list of USB Devices
        """

        # Return Devices
        return self.devices

    @property
    def get_total_devices(self):
        """
        Get USB Devices
        :return: total count of Devices
        """

        # Return Devices
        return len(self.devices)

    @property
    def are_ready(self) -> bool:
        """
        Checks to see if all Devices in Device List are Ready
        :return bool:
        """

        # If any Device is Not Ready in Device List
        if not any(device.is_ready for device in self.devices):
            # Return False
            return False

        # Else
        else:
            # Return True
            return True

    @property
    def are_hdds(self) -> bool:
        """
        Checks to see if all Devices in Device List are HDDs
        :return bool:
        """

        # Return Boolean
        return all(device.is_hdd for device in self.devices)

    @property
    def are_nvme(self) -> bool:
        """
        Checks to see if all Devices in Device List are NVMe
        :return bool:
        """

        # Return Boolean
        return all(device.is_nvme for device in self.devices)

    @property
    def are_ssds(self) -> bool:
        """
        Checks to see if all Devices in Device List are SSDs
        :return bool:
        """

        # Return Boolean
        return all(device.is_ssd for device in self.devices)


@dataclass
class ATAProtocol:
    """
    ATA Protocol
    """

    # Set Helper
    helper: Helper = Helper()

    def __init__(self, device: Device, smartctl: dict):
        """
        Initialize ATA Protocol Collection
        :param device: Device instance
        :param smartctl: Smartctl dictionary
        """

        # If State is Not Ready
        if device.state == "Not Ready":
            # Check Why... First, Sanitize Status...
            ata_sanitize_status = Command(f"hdparm --sanitize-status {device.dut}")

            # Check Sanitize Status
            ata_sanitize_status.run()

            # If Sanitize Operation in Process
            if b"SD2 Sanitize operation In Process" in ata_sanitize_status.get_output():
                # Get Percent Complete
                returned = ata_sanitize_status.get_output().decode("utf-8").split("\n")

                # Remove Empty Strings
                returned = [item for item in returned if item != ""]

                # Decode and Split
                percent = int(returned[-1].split()[-1].strip("()").replace("%", ""))

                # Set State to Sanitizing
                device.state = f"Sanitizing ({percent}%)"

                # Set Flag
                device.flags.append("Sanitize In Progress")

        # Set Properties
        model_name = smartctl.get("model_name", "Not Reported")

        # Vendor
        device.vendor = str(device.determine_brand_by_model_number(model_name)).upper()

        # If Vendor is None
        if device.vendor == none:
            # Determine Vendor by Starting Characters of the Model Number
            device.vendor = self.helper.clean_string(
                device.determine_brand_by_model_number_starts_with(model_name).upper(),
            )

        # Model Number
        device.model_number = self.helper.clean_string(device.determine_model_by_model_number(model_name).upper())

        # Serial Number
        device.serial_number = smartctl.get("serial_number", "Not Reported")

        # Firmware Revision
        device.firmware_revision = smartctl.get("firmware_version", "Not Reported")

        # Transport Revision
        device.transport_revision = smartctl.get("ata_version", dict()).get("string", "Not Reported")

        # Transport Version
        device.transport_version = smartctl.get("sata_version", dict()).get("string", "Not Reported")

        # Rotation Rate
        device.rotation_rate = smartctl.get("rotation_rate", "Not Reported")

        # Form Factor
        device.form_factor = smartctl.get("form_factor", dict()).get("name", "Not Reported")

        # Power On Hours
        device.power_on_hours = (
            smartctl.get("power_on_time", dict()).get("hours", "Not Reported") if device.state == "Ready" else "0",
        )

        # Get Capacity Information
        capacity_info = smartctl.get("user_capacity", dict())

        # Get Capacity in Bytes
        capacity_in_bytes = int(capacity_info.get("bytes", 0))

        # Convert Capacity
        device.size = round(capacity_in_bytes / (1000**3))
        device.bytes = capacity_in_bytes
        device.kilobytes = capacity_in_bytes / 1000
        device.megabytes = capacity_in_bytes / (1000**2)
        device.gigabytes = capacity_in_bytes / (1000**3)
        device.terabytes = capacity_in_bytes / (1000**4)
        device.kibibytes = capacity_in_bytes / 1024
        device.mebibytes = capacity_in_bytes / (1024**2)
        device.gibibytes = capacity_in_bytes / (1024**3)
        device.tebibytes = capacity_in_bytes / (1024**4)

        # Get Sector Information
        device.sectors = int(smartctl.get("user_capacity", dict()).get("blocks", 0))
        device.logical_sector_size = int(smartctl.get("logical_block_size", 0))
        device.physical_sector_size = int(smartctl.get("physical_block_size", 0))

        # S.M.A.R.T Support
        device.smart_supported = smartctl.get("smart_support", dict()).get("available", "Not Reported")
        device.smart_enabled = smartctl.get("smart_support", dict()).get("enabled", "Not Reported")

        # S.M.A.R.T Status
        device.smart_status = smartctl.get("smart_status", dict()).get("passed", "Not Reported")

        # S.M.A.R.T Attributes
        device.smart_attributes = smartctl.get("ata_smart_attributes", dict()).get("table", "Not Reported")

        # If Self Test Supported
        if "ata_smart_data" in smartctl:
            # Set ATA SMART Data
            ata_smart_data = smartctl["ata_smart_data"]

            # If Capabilities
            if "capabilities" in ata_smart_data:
                # Get Capabilities
                capabilities = ata_smart_data["capabilities"]

                # Standard Self Tests
                standard = "self_tests_supported"
                selective = "selective_self_test_supported"
                conveyance = "conveyance_self_test_supported"

                # Set Supported Self Tests
                device.smart_self_tests_supported = capabilities.get(standard, False)
                device.smart_self_tests_selective_supported = capabilities.get(selective, False)
                device.smart_self_tests_conveyance_supported = capabilities.get(conveyance, False)

            # Else
            else:
                # Set to False
                device.smart_self_tests_supported = False
                device.smart_self_tests_conveyance_supported = False
                device.smart_self_tests_selective_supported = False

        # Else
        else:
            # Set to False
            device.smart_self_tests_supported = False
            device.smart_self_tests_conveyance_supported = False
            device.smart_self_tests_selective_supported = False

        # Check ATA Self Test Log
        if "ata_smart_self_test_log" in smartctl:
            # Set Smartctl S.M.A.R.T Self Test Log
            self_test_log = smartctl.get("ata_smart_self_test_log")

            # Self Test Tables
            table = "table"
            standard = "standard"
            extended = "extended"

            # If Extended S.M.A.R.T Self Test Log
            if extended in self_test_log and table in self_test_log.get(extended):
                # Set Self Tests
                self_tests = list(self_test_log[extended][table])

            # If Standard S.M.A.R.T Self Test Log
            elif standard in self_test_log and table in self_test_log.get(standard):
                # Set Self Tests
                self_tests = list(self_test_log[standard][table])

            # Else
            else:
                # No Tests Logged
                self_tests = "No Self Tests Logged"

        # Else
        else:
            # Not Supported
            self_tests = "Not Supported"

        # S.M.A.R.T Self Tests
        device.smart_self_tests = self_tests

        # Get Reallocated Sectors
        device.reallocated_sectors = self.get_smart_attribute_by_id(attribute_id=5, attributes=device.smart_attributes)

        # Get Pending Sectors
        device.pending_reallocated_sectors = self.get_smart_attribute_by_id(
            attribute_id=197,
            attributes=device.smart_attributes,
        )

        # Get Offline Uncorrectable Sectors
        device.offline_uncorrectable_sectors = self.get_smart_attribute_by_id(
            attribute_id=198,
            attributes=device.smart_attributes,
        )

        # Get Device Start/Stop Count
        device.start_stop_count = self.get_smart_attribute_by_id(attribute_id=4, attributes=device.smart_attributes)

        # Get Device Power Cycle Count
        device.power_cycle_count = self.get_smart_attribute_by_id(attribute_id=12, attributes=device.smart_attributes)

        # Get Device Load Cycle Count
        device.load_cycle_count = self.get_smart_attribute_by_id(attribute_id=193, attributes=device.smart_attributes)

        """
        Device Statistics Log Pages
        """

        # Get Device Statistics Pages
        device_statistics_pages = smartctl.get("ata_device_statistics", {}).get("pages", [])

        # Iterate Device Statistics Logs Pages
        for page in device_statistics_pages:
            # Rotating Media Statistics Page
            if page.get("name") == "Rotating Media Statistics":
                # Get Page Information
                device.rotating_media_statistics = None

            # Temperature Statistics
            if page.get("name") == "Temperature Statistics":
                # Extract Table
                temperature_table = page.get("table", [])

                # Iterate Table
                for temperature in temperature_table:
                    # If Specified Maximum Operating Temperature
                    if temperature.get("name") == "Specified Maximum Operating Temperature":
                        # Get Specified Maximum Operating Temperature
                        device.maximum_temperature = temperature.get("value", "Not Reported")

                    # If Specified Minimum Operating Temperature
                    if temperature.get("name") == "Specified Minimum Operating Temperature":
                        # Get Specified Minimum Operating Temperature
                        device.minimum_temperature = temperature.get("value", "Not Reported")

                    # If Current Temperature
                    if temperature.get("name") == "Current Temperature":
                        # Get Current Temperature
                        device.current_temperature = temperature.get("value", "Not Reported")

                    # If Highest Temperature
                    if temperature.get("name") == "Highest Temperature":
                        # Get Highest Temperature
                        device.highest_temperature = temperature.get("value", "Not Reported")

                    # If Lowest Temperature
                    if temperature.get("name") == "Lowest Temperature":
                        # Get Lowest Temperature
                        device.lowest_temperature = temperature.get("value", "Not Reported")

                    # If Average Short Term Temperature
                    if temperature.get("name") == "Average Short Term Temperature":
                        # Get Current Temperature
                        device.average_short_temperature = temperature.get("value", "Not Reported")

                    # If Average Long Term Temperature
                    if temperature.get("name") == "Average Long Term Temperature":
                        # Get Current Temperature
                        device.average_long_temperature = temperature.get("value", "Not Reported")

                    # If Highest Average Short Term Temperature
                    if temperature.get("name") == "Highest Average Short Term Temperature":
                        # Get Current Temperature
                        device.highest_average_short_temperature = temperature.get("value", "Not Reported")

                    # If Lowest Average Short Term Temperature
                    if temperature.get("name") == "Lowest Average Short Term Temperature":
                        # Get Current Temperature
                        device.lowest_average_short_temperature = temperature.get("value", "Not Reported")

                    # If Highest Average Long Term Temperature
                    if temperature.get("name") == "Highest Average Long Term Temperature":
                        # Get Current Temperature
                        device.highest_average_long_temperature = temperature.get("value", "Not Reported")

                    # If Lowest Average Long Term Temperature
                    if temperature.get("name") == "Lowest Average Long Term Temperature":
                        # Get Current Temperature
                        device.lowest_average_long_temperature = temperature.get("value", "Not Reported")

        """
        Grading
        """

        # Set A Grade
        device.cdi_grade = "A"

        # If S.M.A.R.T Fail
        if not device.smart_status:
            # Set F Grade
            device.cdi_grade = "F"
            device.cdi_eligible = False
            device.cdi_certified = False

        # If Maximum Reallocated Sectors exceeded
        if device.reallocated_sectors >= CDI_MAXIMUM_REALLOCATED_SECTORS:
            # Set State to Failed
            device.state = f"Fail"

            # Set F Grade
            device.cdi_grade = "F"
            device.cdi_eligible = False
            device.cdi_certified = False

        # If Maximum Pending Sectors exceeded
        if device.pending_reallocated_sectors >= CDI_MAXIMUM_PENDING_SECTORS:
            # Set State to Failed
            device.state = f"Fail"

            # Set F Grade
            device.cdi_grade = "F"
            device.cdi_eligible = False
            device.cdi_certified = False

        # If Maximum Reallocated Sectors exceeded
        if device.offline_uncorrectable_sectors >= CDI_MAXIMUM_UNCORRECTABLE_ERRORS:
            # Set State to Failed
            device.state = f"Fail"

            # Set F Grade
            device.cdi_grade = "F"
            device.cdi_eligible = False
            device.cdi_certified = False

        # If Temperatures is not None
        if device.highest_temperature is not None and device.maximum_temperature is not None:
            # If Maximum Temperature exceeded
            if device.highest_temperature > device.maximum_temperature:
                # Set State to Failed
                device.state = f"Fail"

                # Set F Grade
                device.cdi_grade = "F"
                device.cdi_eligible = False
                device.cdi_certified = False

        """
        Flags and Labels
        """

        # If S.M.A.R.T Fail
        if not device.smart_status:
            # Set Health to Zero
            device.health = 0

            # Set State to Failed
            device.state = f"Failed"

            # Set Flag
            device.flags.append("Predicted to Fail")

        # If Reallocated Sectors
        if device.reallocated_sectors > 0:
            # Set Flag
            device.flags.append(f"{device.reallocated_sectors} Reallocated Sectors")

        # If Pending Reallocated Sectors
        if device.pending_reallocated_sectors > 0:
            # Set Flag
            device.flags.append(f"{device.pending_reallocated_sectors} Unstable Sectors")

        # If Offline Uncorrectable Sectors
        if device.offline_uncorrectable_sectors > 0:
            # Set Flag
            device.flags.append(f"{device.offline_uncorrectable_sectors} Offline Uncorrectable Errors")

    @staticmethod
    def get_smart_attribute_by_id(
        attributes,
        attribute_id=5,
        actual_value=False,
        worst_value=False,
        threshold=False,
        flags=False,
    ):
        """
        Get ATA S.M.A.R.T. Attribute by ID
        @param attributes: S.M.A.R.T Attributes Object
        @param attribute_id: S.M.A.R.T Attribute ID - Defaults to 5 - Reallocated Sectors Count
        @param actual_value: True if user wants the actual value, otherwise false
        @param worst_value: True if user wants the worst value, otherwise false
        @param threshold: True if user wants the threshold value, otherwise false
        @param flags: True if user wants the flags value, otherwise false
        @return: S.M.A.R.T Attribute Value as selected
        """

        # Default
        default = 0

        # If Reported
        if not attributes == "Not Reported":
            # Loop
            for att in attributes:
                # If ID is found
                if att["id"] == attribute_id:
                    # If Actual
                    if actual_value:
                        # Return Actual Value
                        return att["value"]

                    # If Worst
                    if worst_value:
                        # Return Worst Value
                        return att["worst"]

                    # If Threshold
                    if threshold:
                        # Return Threshold Value
                        return att["threshold"]

                    # If Flags
                    if threshold:
                        # Return Flags
                        return att["flags"]

                    # Else return Attribute Raw Value
                    return att["raw"]["value"]

            # If attribute is not found, return default value
            return default

        else:
            # Return Not Reported
            return default


@dataclass
class NVMeProtocol:
    # Set Helper
    helper: Helper = Helper()

    def __init__(self, device: Device, smartctl: dict):
        # Initialize
        super().__init__()

        # Set Properties
        model_name = smartctl.get("model_name", "Not Reported")

        # Vendor
        device.vendor = str(device.determine_brand_by_model_number(model_name)).upper()

        # If Vendor is None
        if device.vendor == none:
            # Determine Vendor by Starting Characters of the Model Number
            device.vendor = self.helper.clean_string(
                device.determine_brand_by_model_number_starts_with(model_name).upper(),
            )

        # Model Number
        device.model_number = self.helper.clean_string(device.determine_model_by_model_number(model_name).upper())

        # Serial Number
        device.serial_number = smartctl.get("serial_number", "Not Reported")

        # Firmware Revision
        device.firmware_revision = smartctl.get("firmware_version", "Not Reported")

        # Transport Revision
        device.transport_revision = smartctl.get("ata_version", dict()).get("string", "Not Reported")

        # Transport Version
        device.transport_version = smartctl.get("sata_version", dict()).get("string", "Not Reported")

        # Rotation Rate
        device.rotation_rate = smartctl.get("rotation_rate", "Not Reported")

        # Form Factor
        device.form_factor = smartctl.get("form_factor", dict()).get("name", "Not Reported")

        # Power On Hours
        device.power_on_hours = (
            smartctl.get("power_on_time", dict()).get("hours", "Not Reported") if device.state == "Ready" else "0",
        )

        # Get Capacity Information
        capacity_info = smartctl.get("user_capacity", dict())

        # Get Capacity in Bytes
        capacity_in_bytes = int(capacity_info.get("bytes", 0))

        # Convert Capacity
        device.size = round(capacity_in_bytes / (1000**3))
        device.bytes = capacity_in_bytes
        device.kilobytes = capacity_in_bytes / 1000
        device.megabytes = capacity_in_bytes / (1000**2)
        device.gigabytes = capacity_in_bytes / (1000**3)
        device.terabytes = capacity_in_bytes / (1000**4)
        device.kibibytes = capacity_in_bytes / 1024
        device.mebibytes = capacity_in_bytes / (1024**2)
        device.gibibytes = capacity_in_bytes / (1024**3)
        device.tebibytes = capacity_in_bytes / (1024**4)

        # Get Sector Information
        device.sectors = int(smartctl.get("user_capacity", dict()).get("blocks", 0))
        device.logical_sector_size = int(smartctl.get("logical_block_size", 0))
        device.physical_sector_size = int(smartctl.get("physical_block_size", 0))

        # S.M.A.R.T Support
        device.smart_supported = smartctl.get("smart_support", dict()).get("available", "Not Reported")
        device.smart_enabled = smartctl.get("smart_support", dict()).get("enabled", "Not Reported")

        # S.M.A.R.T Status
        device.smart_status = smartctl.get("smart_status", dict()).get("passed", "Not Reported")


@dataclass
class SCSIProtocol:
    def __init__(self, device: Device, smartctl: dict):
        # Initialize
        super().__init__()

        # Device
        self.device = device
        self.smartctl = smartctl

        # Get Vendor
        device.vendor = smartctl.get("scsi_vendor", "Not Reported")

        # Get Model Number
        device.model_number = str(
            device.determine_model_by_model_number(smartctl.get("scsi_model_name", "Not Reported")),
        ).upper()

        # Get Serial Number
        device.serial_number = smartctl.get("serial_number", "Not Reported")

        # Get Firmware Version
        device.firmware_revision = smartctl.get("scsi_revision", "Not Reported")

        # Transport Revision
        device.transport_revision = smartctl.get("scsi_version", "Not Reported")

        # Transport Version
        device.transport_version = smartctl.get("scsi_transport_protocol", "Not Reported")

        # Form Factor
        device.form_factor = smartctl.get("form_factor", {}).get("name")

        # Rotation Rate
        device.rotation_rate = smartctl.get("rotation_rate", "Not Reported")

        # Power on Hours
        device.power_on_hours = smartctl.get("power_on_time", {}).get("hours", 0)

        # Get Capacities
        capacity_info = smartctl.get("user_capacity", {})
        capacity_in_bytes = capacity_info.get("bytes")

        # Check if not Integer
        if not isinstance(capacity_in_bytes, int):
            # If is String and is Digit
            if isinstance(capacity_in_bytes, str) and capacity_in_bytes.isdigit():
                # Set Bytes
                capacity_in_bytes = int(capacity_in_bytes)

            # Else
            else:
                # Set 0
                capacity_in_bytes = 0

        # Capacity in Bytes
        device.bytes = capacity_in_bytes

        # Convert Capacity
        device.kilobytes = capacity_in_bytes / 1000
        device.megabytes = capacity_in_bytes / (1000**2)
        device.gigabytes = capacity_in_bytes / (1000**3)
        device.terabytes = capacity_in_bytes / (1000**4)
        device.kibibytes = capacity_in_bytes / 1024
        device.mebibytes = capacity_in_bytes / (1024**2)
        device.gibibytes = capacity_in_bytes / (1024**3)
        device.tebibytes = capacity_in_bytes / (1024**4)

        # Get Sector Information
        device.sectors = int(smartctl.get("user_capacity", dict()).get("blocks", 0))
        device.logical_sector_size = int(smartctl.get("logical_block_size", 0))
        device.physical_sector_size = int(smartctl.get("physical_block_size", 0))

        # S.M.A.R.T Support
        device.smart_supported = smartctl.get("smart_support", dict()).get("available", "Not Reported")
        device.smart_enabled = smartctl.get("smart_support", dict()).get("enabled", "Not Reported")

        # S.M.A.R.T Status
        device.smart_status = smartctl.get("smart_status", dict()).get("passed", "Not Reported")

        # S.M.A.R.T Attributes
        device.smart_attributes = smartctl.get("scsi_error_counter_log", "Not Reported")

        """
        Self Tests
        """

        self_tests = []

        # Loop Key, Values
        for key, value in smartctl.items():
            # If Self Test in not in Key
            if "scsi_self_test_" not in key:
                # Skip
                continue

            # Append Key
            self_tests.append(value)

        # Set Self Tests
        device.smart_self_tests = self_tests

        # Get Grown Defects
        grown_defects = smartctl.get("scsi_grown_defect_list", "Not Reported")

        # If Grown Defects not reported
        if grown_defects == "Not Reported":
            # Set Grown Defects
            device.reallocated_sectors = -1

        # Else
        else:
            # Set Grown Defects
            device.reallocated_sectors = grown_defects

        """
        Uncorrectable Errors
        """

        # If Error Counter Log
        if "scsi_error_counter_log" in smartctl:
            # If Read Errors in Log
            if "read" in smartctl["scsi_error_counter_log"]:
                # Set Read Errors
                read_errors = smartctl["scsi_error_counter_log"]["read"]["total_uncorrected_errors"]

            # Else
            else:
                # Set Read Errors to Zero
                read_errors = 0

            # If Write Errors in Log
            if "write" in smartctl["scsi_error_counter_log"]:
                # Set Write Errors
                write_errors = smartctl["scsi_error_counter_log"]["write"]["total_uncorrected_errors"]

            # Else
            else:
                # Set Write Errors to Zero
                write_errors = 0

            # If Verify Errors in Log
            if "verify" in smartctl["scsi_error_counter_log"]:
                # Set Verify Errors
                verify_errors = smartctl["scsi_error_counter_log"]["verify"]["total_uncorrected_errors"]

            # Else
            else:
                # Set Verify Errors to Zero
                verify_errors = 0

            # If Verify Errors
            if verify_errors:
                # Count Total including Verify Errors
                uncorrectable_errors = int(read_errors) + int(write_errors) + int(verify_errors)

            # Else
            else:
                # Count Total excluding Verify Errors
                uncorrectable_errors = int(read_errors) + int(write_errors)

        # Else
        else:
            # Set Uncorrectable Errors to None
            uncorrectable_errors = None

        # Convert Uncorrectable Errors
        device.offline_uncorrectable_sectors = int(uncorrectable_errors) if uncorrectable_errors is not None else -1

        """
        Grading
        """

        # Set A Grade
        device.cdi_grade = "A"

        # If S.M.A.R.T Fail
        if not device.smart_status:
            # Set F Grade
            device.cdi_grade = "F"
            device.cdi_eligible = False
            device.cdi_certified = False

        # If Maximum Reallocated Sectors exceeded
        if device.reallocated_sectors >= CDI_MAXIMUM_REALLOCATED_SECTORS:
            # Set State to Failed
            device.state = f"Fail"

            # Set F Grade
            device.cdi_grade = "F"
            device.cdi_eligible = False
            device.cdi_certified = False

        # If Maximum Reallocated Sectors exceeded
        if device.offline_uncorrectable_sectors >= CDI_MAXIMUM_UNCORRECTABLE_ERRORS:
            # Set State to Failed
            device.state = f"Fail"

            # Set F Grade
            device.cdi_grade = "F"
            device.cdi_eligible = False
            device.cdi_certified = False

        # If Temperatures is not None
        if device.highest_temperature is not None and device.maximum_temperature is not None:
            # If Maximum Temperature exceeded
            if device.highest_temperature > device.maximum_temperature:
                # Set State to Failed
                device.state = f"Fail"

                # Set F Grade
                device.cdi_grade = "F"
                device.cdi_eligible = False
                device.cdi_certified = False

        """
        Flags and Labels
        """

        # If S.M.A.R.T Fail
        if not device.smart_status:
            # Set Health to Zero
            device.health = 0

            # Set State to Failed
            device.state = f"Failed"

            # Set Flag
            device.flags.append("Predicted to Fail")

        # If Reallocated Sectors
        if device.reallocated_sectors > 0:
            # Set Flag
            device.flags.append(f"{device.reallocated_sectors} Reallocated Sectors")

        # If Offline Uncorrectable Sectors
        if device.offline_uncorrectable_sectors > 0:
            # Set Flag
            device.flags.append(f"{device.offline_uncorrectable_sectors} Offline Uncorrectable Errors")


@dataclass
class USBProtocol:
    def __init__(self, device: Device):
        # Initialize
        super().__init__()

        # Device
        self.device = device

    def initialize(self):
        pass
