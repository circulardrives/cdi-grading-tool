#
# Copyright (c) 2025 Circular Drive Initiative.
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
Constants and enumerations for CDI Health.

Centralized location for magic numbers, strings, and configuration values.
"""

from __future__ import annotations

from enum import Enum


class Protocol(str, Enum):
    """Storage device protocols."""

    ATA = "ata"
    NVME = "nvme"
    SCSI = "scsi"


class HealthGrade(str, Enum):
    """Health grade levels."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class HealthStatus(str, Enum):
    """Health status levels."""

    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
    FAILED = "Failed"


class Severity(str, Enum):
    """Severity levels for issues."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"
    YAML = "yaml"


class ReportFormat(str, Enum):
    """Report format options."""

    HTML = "html"
    PDF = "pdf"


# Scoring constants
BASE_SCORE = 100
SMART_FAILURE_DEDUCTION = 50
SELFTEST_FAILURE_DEDUCTION = 50
REALLOCATED_SECTOR_DEDUCTION = 5
PENDING_SECTOR_DEDUCTION = 5
UNCORRECTABLE_ERROR_DEDUCTION = 5
THRESHOLD_EXCEEDED_DEDUCTION = 25
TEMPERATURE_WARNING_DEDUCTION = 5
TEMPERATURE_CRITICAL_DEDUCTION = 15

# Grade thresholds
GRADE_A_MIN = 90
GRADE_B_MIN = 75
GRADE_C_MIN = 60
GRADE_D_MIN = 40
GRADE_F_MAX = 39

# NVMe self-test constants
NVME_SELFTEST_LOG_PAGE = 0x06
NVME_SELFTEST_LOG_LENGTH = 512
NVME_OACS_SELFTEST_BIT = 0x10  # Bit 4
NVME_DSTS_SHORT = 0x1
NVME_DSTS_EXTENDED = 0x2
NVME_DSTS_ABORT = 0xF

# Terminal width constants
MIN_TERMINAL_WIDTH = 60
COMPACT_LAYOUT_THRESHOLD = 100
MAX_HEADER_WIDTH = 120

# Time constants (in seconds)
DEFAULT_WATCH_INTERVAL = 60
SELFTEST_POLL_INTERVAL = 30

# File paths
DEFAULT_CONFIG_FILE = "thresholds.yaml"
