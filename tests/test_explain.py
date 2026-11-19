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

"""Tests for grading explainability helpers and CLI --explain path."""

from __future__ import annotations

import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

from cdi_health.classes.colors import Colors
from cdi_health.classes.explain import (
    ExplainFormatter,
    attach_explanation,
    certification_blockers,
    certification_rationale,
    explanation_fields,
    format_explanations,
)
from cdi_health.classes.formatter import JSONFormatter
from cdi_health.classes.scoring import HealthScore, ScoreDeduction
from cdi_health.cli import cmd_scan, create_parser


def _score(
    *,
    score: int = 100,
    grade: str = "A",
    status: str = "Excellent",
    is_certified: bool = True,
    deductions: list[ScoreDeduction] | None = None,
    grading_profile: str = "abcdf",
    certification: str | None = None,
) -> HealthScore:
    if certification is None:
        certification = "true" if is_certified else "false"
    return HealthScore(
        score=score,
        grade=grade,
        status=status,
        deductions=deductions or [],
        is_certified=is_certified,
        grading_profile=grading_profile,
        certification=certification,
    )


class TestCertificationRationale:
    def test_certified_rationale(self) -> None:
        score = _score(grade="A", status="Excellent", is_certified=True)
        text = certification_rationale(score)
        assert "Certified because grade A" in text
        assert "no critical deductions" in text
        assert certification_blockers(score) == []

    def test_not_certified_grade_blocker(self) -> None:
        score = _score(score=0, grade="F", status="Failed", is_certified=False)
        blockers = certification_blockers(score)
        assert any("grade is F" in b and "A, B, or C" in b for b in blockers)
        assert certification_rationale(score).startswith("Not certified because")

    def test_binary_profile_rejects_grade_c(self) -> None:
        score = _score(
            score=50,
            grade="C",
            status="Fair",
            is_certified=False,
            grading_profile="binary",
        )
        blockers = certification_blockers(score)
        assert any("grade is C" in b and "A or B" in b for b in blockers)

    def test_critical_deduction_blocker(self) -> None:
        deduction = ScoreDeduction(
            reason="SMART status failed",
            points=50,
            severity="critical",
            field="smart_status",
            value=False,
            threshold=True,
        )
        score = _score(
            score=0,
            grade="F",
            status="Failed",
            is_certified=False,
            deductions=[deduction],
        )
        blockers = certification_blockers(score)
        assert any("critical deduction: SMART status failed" in b for b in blockers)
        assert any("grade is F" in b for b in blockers)


class TestExplanationFields:
    def test_stable_structure(self) -> None:
        deduction = ScoreDeduction(
            reason="Temperature warning",
            points=5,
            severity="warning",
            field="current_temperature",
            value=72,
            threshold=70,
        )
        score = _score(
            score=95,
            grade="A",
            status="Excellent",
            is_certified=True,
            deductions=[deduction],
        )
        fields = explanation_fields(score)
        assert fields["points_deducted"] == 5
        assert "certification_rationale" in fields
        assert isinstance(fields["certification_blockers"], list)
        grading = fields["grading_explanation"]
        assert grading["score"] == 95
        assert grading["grade"] == "A"
        assert grading["deductions"][0]["field"] == "current_temperature"
        assert grading["deductions"][0]["threshold"] == 70
        assert grading["deductions"][0]["points"] == 5

    def test_attach_explanation_includes_score_and_rationale(self, sample_nvme_device: dict) -> None:
        Colors.disable()
        enriched = attach_explanation(sample_nvme_device)
        assert "health_score" in enriched
        assert "health_grade" in enriched
        assert "deductions" in enriched
        assert "certification_rationale" in enriched
        assert "grading_explanation" in enriched
        assert isinstance(enriched["grading_explanation"]["deductions"], list)


class TestExplainFormatter:
    def test_format_empty(self) -> None:
        assert ExplainFormatter().format([]) == "No devices found."

    def test_format_includes_sections(self, sample_nvme_device: dict) -> None:
        Colors.disable()
        text = format_explanations([sample_nvme_device])
        assert "Grading Explainability" in text
        assert "Grade:" in text
        assert "Certification:" in text
        assert "Deductions" in text

    def test_format_lists_deduction_details(self) -> None:
        Colors.disable()
        device = {
            "dut": "/dev/sda",
            "model_number": "TestDrive",
            "serial_number": "SN1",
            "transport_protocol": "ATA",
            "media_type": "HDD",
            "smart_status": False,
            "smart_supported": True,
        }
        text = format_explanations([device])
        assert "Certified:" in text
        assert "Not certified" in text or "critical" in text.lower() or "Grade:" in text

    def test_format_shows_attribute_grade_not_cosmetic_points(self) -> None:
        """#119: abcdf graduated attributes show grade impact, not fake point totals."""
        from cdi_health.classes.config import ThresholdConfig

        Colors.disable()
        ThresholdConfig.reset_instance()
        ThresholdConfig.get_instance().set_grading_profile("abcdf")
        device = {
            "dut": "/dev/sg0",
            "model_number": "SAS-Drive",
            "serial_number": "SN-GROWN",
            "transport_protocol": "SCSI",
            "media_type": "HDD",
            "smart_status": "PASSED",
            "grown_defects": 25,
            "uncorrected_errors": 0,
            "power_on_hours": 1000,
            "state": "Ready",
        }
        text = format_explanations([device])
        assert "grade C" in text or "graded attributes" in text
        assert "points total" not in text


class TestJSONIncludesExplainability:
    def test_json_enrichment_has_explain_fields(self, sample_nvme_device: dict) -> None:
        data = json.loads(JSONFormatter().format([sample_nvme_device]))
        assert len(data) == 1
        assert "certification_rationale" in data[0]
        assert "certification_blockers" in data[0]
        assert "grading_explanation" in data[0]
        assert "deductions" in data[0]


# A drive whose SMART data could not be read. The scoring engine sees no
# defects in the empty record, so it scores a clean A / 100 / certified.
UNREADABLE_DRIVE = {
    "dut": "/dev/nvme0",
    "model_number": "UNREADABLE NVME",
    "serial_number": "UNREADABLE-1",
    "transport_protocol": "NVMe",
    "media_type": "SSD",
    "state": "Ready",
    "smart_data_readable": False,
}
# A drive that could not be opened at all scores F on "Device not ready".
UNOPENABLE_DRIVE = {
    "dut": "/dev/sdq",
    "model_number": "Not Reported",
    "serial_number": "Not Reported",
    "transport_protocol": "Unknown",
    "state": "Not Ready",
    "grading_status": "UNGRADED",
    "ungraded_reasons": ["DEVICE_OPEN_FAILURE"],
    "ungraded_detail": "smartctl open failed: Permission denied",
    "smart_data_readable": False,
}


class TestUngradedDrivesNeverShowAGrade:
    """§15: an UNGRADED drive must not carry a letter grade in any output."""

    def test_explain_does_not_grade_an_unreadable_drive(self) -> None:
        Colors.disable()
        text = format_explanations([UNREADABLE_DRIVE])
        assert "Grade: UNGRADED" in text
        assert "Not graded: SMART_UNREADABLE" in text
        assert "Certified: No" in text
        assert "Grade: A" not in text
        assert "Certified: Yes" not in text
        assert "Score:" not in text

    def test_explain_does_not_fail_an_unopenable_drive(self) -> None:
        Colors.disable()
        text = format_explanations([UNOPENABLE_DRIVE])
        assert "Grade: UNGRADED" in text
        assert "DEVICE_OPEN_FAILURE" in text
        assert "Permission denied" in text
        assert "Grade: F" not in text
        assert "grade is F" not in text

    def test_explain_still_grades_readable_drives_alongside(self, sample_nvme_device: dict) -> None:
        Colors.disable()
        text = format_explanations([UNREADABLE_DRIVE, sample_nvme_device])
        assert text.count("Grade: UNGRADED") == 1
        assert "Score:" in text

    def test_json_carries_no_grade_for_an_unreadable_drive(self) -> None:
        record = json.loads(JSONFormatter().format([UNREADABLE_DRIVE]))[0]
        assert record["health_grade"] == "UNGRADED"
        assert record["is_certified"] is False
        assert record["certification"] == "false"
        assert record["revert_certified"] == "false"
        assert record["certification_blockers"] == ["not graded: SMART_UNREADABLE"]

        explanation = record["grading_explanation"]
        assert explanation["grade"] == "UNGRADED"
        assert explanation["score"] is None
        assert explanation["is_certified"] is False
        assert explanation["certification_rationale"] == record["certification_rationale"]
        assert "Not graded" in explanation["certification_rationale"]

    def test_json_carries_no_grade_for_an_unopenable_drive(self) -> None:
        record = json.loads(JSONFormatter().format([UNOPENABLE_DRIVE]))[0]
        assert record["certification"] == "false"
        assert record["grading_explanation"]["grade"] == "UNGRADED"
        assert all("grade is F" not in blocker for blocker in record["certification_blockers"])
        assert all("grade is F" not in blocker for blocker in record["grading_explanation"]["certification_blockers"])


class TestExplainCLI:
    def test_parser_explain_flag(self) -> None:
        parser = create_parser()
        args = parser.parse_args(["scan", "--explain"])
        assert args.explain is True

    @patch("cdi_health.cli.scan_devices_mock")
    @patch("cdi_health.cli.setup_logging")
    def test_cmd_scan_explain_table(
        self, _setup: MagicMock, mock_scan: MagicMock, sample_nvme_device: dict, capsys
    ) -> None:
        Colors.disable()
        mock_scan.return_value = [sample_nvme_device]
        args = Namespace(
            mock_data="test/path",
            mock_file=None,
            ignore_ata=False,
            ignore_nvme=False,
            ignore_scsi=False,
            output="table",
            details=True,
            explain=True,
            device=None,
            verbose=False,
            no_color=True,
            config=None,
        )
        assert cmd_scan(args) == 0
        out = capsys.readouterr().out
        assert "Grading Explainability" in out
        assert "Certification:" in out
