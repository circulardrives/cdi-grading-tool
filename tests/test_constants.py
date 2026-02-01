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

"""Tests for constants module."""

from __future__ import annotations

import pytest

from cdi_health.constants import (
    BASE_SCORE,
    GRADE_A_MIN,
    GRADE_B_MIN,
    GRADE_C_MIN,
    GRADE_D_MIN,
    GRADE_F_MAX,
    HealthGrade,
    HealthStatus,
    OutputFormat,
    Protocol,
    ReportFormat,
    Severity,
)


class TestEnums:
    """Test enum classes."""

    def test_protocol_enum(self) -> None:
        """Test Protocol enum."""
        assert Protocol.ATA == "ata"
        assert Protocol.NVME == "nvme"
        assert Protocol.SCSI == "scsi"

    def test_health_grade_enum(self) -> None:
        """Test HealthGrade enum."""
        assert HealthGrade.A == "A"
        assert HealthGrade.F == "F"

    def test_health_status_enum(self) -> None:
        """Test HealthStatus enum."""
        assert HealthStatus.EXCELLENT == "Excellent"
        assert HealthStatus.FAILED == "Failed"

    def test_severity_enum(self) -> None:
        """Test Severity enum."""
        assert Severity.INFO == "info"
        assert Severity.CRITICAL == "critical"

    def test_output_format_enum(self) -> None:
        """Test OutputFormat enum."""
        assert OutputFormat.TABLE == "table"
        assert OutputFormat.JSON == "json"

    def test_report_format_enum(self) -> None:
        """Test ReportFormat enum."""
        assert ReportFormat.HTML == "html"
        assert ReportFormat.PDF == "pdf"


class TestConstants:
    """Test constant values."""

    def test_base_score(self) -> None:
        """Test BASE_SCORE constant."""
        assert BASE_SCORE == 100

    def test_grade_thresholds(self) -> None:
        """Test grade threshold constants."""
        assert GRADE_A_MIN == 90
        assert GRADE_B_MIN == 75
        assert GRADE_C_MIN == 60
        assert GRADE_D_MIN == 40
        assert GRADE_F_MAX == 39
        
        # Verify thresholds are in correct order
        assert GRADE_A_MIN > GRADE_B_MIN > GRADE_C_MIN > GRADE_D_MIN > GRADE_F_MAX
