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
Circular Drive Initiative - Configuration Class

@language    Python 3.12
@framework   PySide 6
@version     0.0.1
"""

from __future__ import annotations

# Modules
import configparser
import os

# Exceptions
from cdi_health.classes.exceptions import ConfigurationException

# Constants
from cdi_health.constants import configuration_file


class Configuration:
    """
    Configuration Class
    """

    def __init__(self, file: str = configuration_file):
        """
        Constructor
        :param file:
        """

        # Instantiate Configuration Parser
        self.configuration: configparser.ConfigParser = configparser.ConfigParser()

        # Set Configuration File
        self.configuration_file: str = file

        """
        Properties
        """

        # General
        self.language = None
        self.fullscreen = None

        # Network
        self.use_wifi = None
        self.use_ethernet = None

        # WiFi
        self.wifi_ssid = None
        self.wifi_password = None
        self.wifi_channel = None
        self.wifi_channel_name = None

        # Energy
        self.shutdown_when_complete = None

        # Users
        self.users_list = None

        # Ignore
        self.ignore_ata = None
        self.ignore_fusion_io = None
        self.ignore_ide = None
        self.ignore_nvme = None
        self.ignore_scsi = None
        self.ignore_usb = None
        self.ignore_usb = None
        self.ignore_sd = None

        # Reference Numbers
        self.use_reference_numbers = None
        self.force_reference_numbers = None

        # Lot Numbers
        self.use_lot_numbers = None
        self.force_lot_numbers = None

        # Asset Numbers
        self.use_asset_numbers = None
        self.force_asset_numbers = None

        # Custom Fields
        self.use_global_custom_fields = None
        self.use_device_custom_fields = None

        # Logging
        self.use_local_logging = None
        self.use_samba_logging = None
        self.use_ftp_logging = None
        self.use_https_logging = None
        self.use_database_logging = None

        # Logging Path
        self.local_logging_path = None

        # Logging Formats
        self.local_logging_csv = None
        self.local_logging_html = None
        self.local_logging_json = None
        self.local_logging_pdf = None
        self.local_logging_xml = None

        # FTP Configuration
        self.ftp_ip_address = None
        self.ftp_hostname = None
        self.ftp_port = None
        self.ftp_username = None
        self.ftp_password = None
        self.ftp_directory = None

        # Database Configuration
        self.database_ip_address = None
        self.database_username = None
        self.database_password = None
        self.database_name = None

        # Samba Configuration
        self.samba_ip_address = None
        self.samba_hostname = None
        self.samba_domain = None
        self.samba_username = None
        self.samba_password = None
        self.samba_directory = None

        # HTTPS Configuration
        self.https_url = None
        self.https_username = None
        self.https_password = None

        # Device Table Column Configuration
        self.devices_table_dut_visible = True
        self.devices_table_state_visible = True
        self.devices_table_type_visible = True
        self.devices_table_protocol_visible = True
        self.devices_table_brand_visible = True
        self.devices_table_model_visible = True
        self.devices_table_serial_visible = True
        self.devices_table_firmware_visible = True
        self.devices_table_capacity_visible = True
        self.devices_table_sector_size_visible = True
        self.devices_table_poh_visible = True
        self.devices_table_speed_visible = True
        self.devices_table_temp_visible = True
        self.devices_table_smart_visible = True
        self.devices_table_health_visible = True
        self.devices_table_comments_visible = True

        # Jobs Column Visibility
        self.jobs_column_dut = True
        self.jobs_column_reference = True
        self.jobs_column_brand = True
        self.jobs_column_model = True
        self.jobs_column_serial = True
        self.jobs_column_capacity = True
        self.jobs_column_method = True
        self.jobs_column_state = True
        self.jobs_column_progress = True
        self.jobs_column_result = True
        self.jobs_column_comments = True

        # Custom Fields
        self.custom_field_1 = True
        self.custom_field_2 = True
        self.custom_field_3 = True
        self.custom_field_4 = True
        self.custom_field_5 = True
        self.custom_field_6 = True
        self.custom_field_7 = True
        self.custom_field_8 = True
        self.custom_field_9 = True
        self.custom_field_10 = True
        self.custom_field_11 = True
        self.custom_field_12 = True
        self.custom_field_13 = True
        self.custom_field_14 = True
        self.custom_field_15 = True

        # Try
        try:
            # Load Configuration
            self.load()

        # If Configuration Exception
        except ConfigurationException as configuration:
            # Print
            print(configuration)

    def load(self):
        """
        Load Configuration
        :return:
        """

        # If OS Path doesn't exist
        if not os.path.exists(self.configuration_file):
            # Raise Configuration Exception
            raise ConfigurationException(f"Warning: Configuration file '{self.configuration_file}' not found.")

        # Read Configuration File
        self.configuration.read(self.configuration_file)

    def read(self):
        """
        Read Configuration
        :return:
        """

        # If OS Path doesn't exist
        if not os.path.exists(self.configuration_file):
            # Raise Configuration Exception
            raise ConfigurationException(f"Warning: Configuration file '{self.configuration_file}' not found.")

        # Read Configuration File
        self.configuration.read(self.configuration_file)

    def save(self):
        """
        Save Configuration
        :return:
        """

        # If OS Path doesn't exist
        if not os.path.exists(self.configuration_file):
            # Raise Configuration Exception
            raise ConfigurationException(f"Warning: Configuration file '{self.configuration_file}' not found.")

        # Open Configuration File
        with open(self.configuration_file, "w") as config_file:
            # Write Configuration File
            self.configuration.write(config_file)

    def set(self, section, key, value):
        """
        Set a property in the configuration.
        :param section: Configuration section.
        :param key: Property key.
        :param value: Property value.
        """

        # If Configuration doesn't contain Section
        if not self.configuration.has_section(section):
            # Add Section
            self.configuration.add_section(section)

        # Set Value
        self.configuration.set(section, key, str(value))

    def get(self, section, key):
        """
        Get a property from the configuration.
        :param section: Configuration section.
        :param key: Property key.
        :return: Property value or None if not found.
        """

        # If Configuration has Section and has related Option
        if self.configuration.has_section(section) and self.configuration.has_option(section, key):
            # Return Value
            return self.configuration.get(section, key)

        # Return None
        return None

    def get_boolean(self, section, key):
        """
        Get a Boolean property from the configuration.
        :param section: Configuration section.
        :param key: Property key.
        :return: Property value or None if not found.
        """

        # If Configuration has Section and has related Option
        if self.configuration.has_section(section) and self.configuration.has_option(section, key):
            # Return Value
            return self.configuration.getboolean(section, key)

        # Return None
        return None

    def get_int(self, section, key):
        """
        Get an Integer property from the configuration.
        :param section: Configuration section.
        :param key: Property key.
        :return: Property value or None if not found.
        """

        # If Configuration has Section and has related Option
        if self.configuration.has_section(section) and self.configuration.has_option(section, key):
            # Return Value
            return self.configuration.getint(section, key)

        # Return None
        return None

    def get_float(self, section, key):
        """
        Get a Float property from the configuration.
        :param section: Configuration section.
        :param key: Property key.
        :return: Property value or None if not found.
        """

        # If Configuration has Section and has related Option
        if self.configuration.has_section(section) and self.configuration.has_option(section, key):
            # Return Value
            return self.configuration.getfloat(section, key)

        # Return None
        return None
