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
Configuration Management for CDI Health

Provides configurable thresholds loaded from YAML files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Try to import yaml, fall back to None if not available
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

# Default thresholds (fallback if no config file or yaml unavailable)
DEFAULT_THRESHOLDS = {
    "smart": {
        "expected_result": "Pass",
        "expected_self_test_result": "Pass",
    },
    "ata": {
        "maximum_reallocated_sectors": 10,
        "maximum_pending_sectors": 10,
        "maximum_uncorrectable_errors": 10,
    },
    "nvme": {
        "maximum_percentage_used": 100,
        "minimum_available_spare": 97,
    },
    "scsi": {
        "maximum_grown_defects": 10,
        "maximum_uncorrected_errors": 10,
    },
    "temperature": {
        "maximum_operating": 60,
        "warning": 55,
    },
    "grading": {
        "hdd_sector_concern_threshold": 2,
        "hdd_sector_defect_max_deduction_points": 10,
    },
}


class ThresholdConfig:
    """
    Configuration class for CDI Health thresholds.

    Supports loading from YAML files and provides easy access to threshold values.
    """

    _instance: ThresholdConfig = None

    def __init__(self, config_path: str | Path = None):
        """
        Initialize threshold configuration.

        :param config_path: Optional path to YAML config file
        """
        self._config: dict = {}
        self._config_path: Path | None = None

        # Start with defaults
        self._config = self._deep_copy(DEFAULT_THRESHOLDS)

        # Load from file if provided
        if config_path:
            self.load_from_file(config_path)

    @classmethod
    def get_instance(cls) -> ThresholdConfig:
        """
        Get the singleton instance.

        :return: ThresholdConfig instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    @classmethod
    def configure(cls, config_path: str | Path = None) -> ThresholdConfig:
        """
        Configure the global instance with a config file.

        :param config_path: Path to YAML config file
        :return: Configured ThresholdConfig instance
        """
        cls._instance = cls(config_path)
        return cls._instance

    def load_from_file(self, path: str | Path) -> bool:
        """
        Load configuration from a YAML file.

        :param path: Path to YAML file
        :return: True if loaded successfully, False otherwise
        """
        if not YAML_AVAILABLE:
            print("Warning: PyYAML not installed, using default thresholds")
            return False

        path = Path(path)

        if not path.exists():
            print(f"Warning: Config file not found: {path}")
            return False

        try:
            with open(path, encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f)

            if loaded_config:
                # Merge with defaults (loaded config overrides defaults)
                self._config = self._merge_dicts(DEFAULT_THRESHOLDS, loaded_config)
                self._config_path = path
                return True

        except yaml.YAMLError as e:
            print(f"Warning: Failed to parse config file: {e}")
            return False
        except Exception as e:
            print(f"Warning: Error loading config file: {e}")
            return False

        return False

    def load_from_dict(self, config: dict) -> None:
        """
        Load configuration from a dictionary.

        :param config: Configuration dictionary
        """
        self._config = self._merge_dicts(DEFAULT_THRESHOLDS, config)

    def _merge_dicts(self, base: dict, override: dict) -> dict:
        """
        Deep merge two dictionaries.

        :param base: Base dictionary
        :param override: Dictionary with override values
        :return: Merged dictionary
        """
        result = self._deep_copy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    def _deep_copy(self, d: dict) -> dict:
        """Deep copy a dictionary."""
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = self._deep_copy(value)
            else:
                result[key] = value
        return result

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a nested configuration value.

        :param keys: Path to the value (e.g., "ata", "maximum_reallocated_sectors")
        :param default: Default value if not found
        :return: Configuration value
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    # SMART thresholds
    @property
    def expected_smart_result(self) -> str:
        """Expected SMART status result."""
        return self.get("smart", "expected_result", default="Pass")

    @property
    def expected_smart_self_test_result(self) -> str:
        """Expected SMART self-test result."""
        return self.get("smart", "expected_self_test_result", default="Pass")

    # ATA thresholds
    @property
    def maximum_reallocated_sectors(self) -> int:
        """Maximum reallocated sectors for ATA devices."""
        return self.get("ata", "maximum_reallocated_sectors", default=10)

    @property
    def maximum_pending_sectors(self) -> int:
        """Maximum pending sectors for ATA devices."""
        return self.get("ata", "maximum_pending_sectors", default=10)

    @property
    def maximum_uncorrectable_errors(self) -> int:
        """Maximum uncorrectable errors for ATA devices."""
        return self.get("ata", "maximum_uncorrectable_errors", default=10)

    # NVMe thresholds
    @property
    def maximum_ssd_percentage_used(self) -> int:
        """Maximum percentage used for NVMe SSDs."""
        return self.get("nvme", "maximum_percentage_used", default=100)

    @property
    def minimum_ssd_available_spare(self) -> int:
        """Minimum available spare percentage for NVMe SSDs."""
        return self.get("nvme", "minimum_available_spare", default=97)

    # SCSI thresholds
    @property
    def maximum_grown_defects(self) -> int:
        """Maximum grown defects for SCSI devices."""
        return self.get("scsi", "maximum_grown_defects", default=10)

    @property
    def maximum_scsi_uncorrected_errors(self) -> int:
        """Maximum uncorrected errors for SCSI devices."""
        return self.get("scsi", "maximum_uncorrected_errors", default=10)

    # Temperature thresholds
    @property
    def maximum_operating_temperature(self) -> int:
        """Maximum operating temperature in Celsius."""
        return self.get("temperature", "maximum_operating", default=60)

    @property
    def warning_temperature(self) -> int:
        """Warning temperature in Celsius."""
        return self.get("temperature", "warning", default=55)

    @property
    def hdd_sector_concern_threshold(self) -> int:
        """Reallocated/pending/grown counts at or below this value incur no score deduction."""
        return self.get("grading", "hdd_sector_concern_threshold", default=2)

    @property
    def hdd_sector_defect_max_deduction_points(self) -> int:
        """Maximum score points deducted per defect type at failure threshold (e.g. 10 sectors)."""
        return self.get("grading", "hdd_sector_defect_max_deduction_points", default=10)

    def to_dict(self) -> dict:
        """
        Get full configuration as dictionary.

        :return: Configuration dictionary
        """
        return self._deep_copy(self._config)

    def __repr__(self) -> str:
        return f"ThresholdConfig(path={self._config_path})"


# Global configuration access function
def get_config() -> ThresholdConfig:
    """
    Get the global threshold configuration.

    :return: ThresholdConfig instance
    """
    return ThresholdConfig.get_instance()


def configure_thresholds(config_path: str | Path = None) -> ThresholdConfig:
    """
    Configure the global thresholds from a file.

    :param config_path: Path to YAML config file
    :return: ThresholdConfig instance
    """
    return ThresholdConfig.configure(config_path)


def get_default_config_path() -> Path | None:
    """
    Get the default config file path.

    :return: Path to default thresholds.yaml or None if not found
    """
    # Check for config in package directory
    package_dir = Path(__file__).parent.parent
    default_path = package_dir / "config" / "thresholds.yaml"

    if default_path.exists():
        return default_path

    return None
