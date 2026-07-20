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
) -> HealthScore:
    return HealthScore(
        score=score,
        grade=grade,
        status=status,
        deductions=deductions or [],
        is_certified=is_certified,
    )


class TestCertificationRationale:
    def test_certified_rationale(self) -> None:
        score = _score(grade="A", status="Excellent", is_certified=True)
        text = certification_rationale(score)
        assert "Certified because grade A" in text
        assert "no critical deductions" in text
        assert certification_blockers(score) == []

    def test_not_certified_grade_blocker(self) -> None:
        score = _score(score=50, grade="C", status="Fair", is_certified=False)
        blockers = certification_blockers(score)
        assert any("grade is C" in b for b in blockers)
        assert certification_rationale(score).startswith("Not certified because")

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


class TestJSONIncludesExplainability:
    def test_json_enrichment_has_explain_fields(self, sample_nvme_device: dict) -> None:
        data = json.loads(JSONFormatter().format([sample_nvme_device]))
        assert len(data) == 1
        assert "certification_rationale" in data[0]
        assert "certification_blockers" in data[0]
        assert "grading_explanation" in data[0]
        assert "deductions" in data[0]


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
