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
Revert Drive Grading Standard v2.0 regression harness (gap-analysis Finding 8 / #124).

Loads every fixture under ``tests/fixtures/revert_standard/``, grades each via
the public ``calculate_health_score`` API, and compares against:

1. A hardcoded expected-grade table (Finding 8 method / report serial pins)
2. An independent Revert Standard grade computed from the fixture JSON

Agreement is reported; mismatches fail once graduated scoring is ready.
SSD wear fixtures that still lack graduated scoring are marked xfail for
#116/#115/#121.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.revert_standard_helpers import (
    EXPECTED_GRADES,
    FIXTURE_SECTIONS,
    PENDING_GRADUATED_SCORING,
    certification_for_grade,
    compute_standard_grade,
    grade_fixture_with_tool,
    list_fixture_paths,
    load_fixture,
)

FIXTURE_PATHS = list_fixture_paths()


def _fixture_params(*, apply_pending_xfail: bool = False) -> list:
    """Build parametrize entries; optionally xfail pending graduated-scoring cases."""
    params = []
    for path in FIXTURE_PATHS:
        marks = []
        if apply_pending_xfail and path.stem in PENDING_GRADUATED_SCORING:
            marks.append(
                pytest.mark.xfail(
                    reason="pending graduated scoring for #116/#115/#121",
                    strict=False,
                )
            )
        params.append(pytest.param(path, id=path.stem, marks=marks))
    return params


@pytest.mark.parametrize("fixture_path", _fixture_params())
def test_fixture_covered_by_expected_table(fixture_path: Path) -> None:
    """Every on-disk fixture must have a hardcoded expected grade."""
    assert fixture_path.stem in EXPECTED_GRADES, (
        f"fixture {fixture_path.name} missing from EXPECTED_GRADES "
        f"(section={FIXTURE_SECTIONS.get(fixture_path.stem, '?')})"
    )


@pytest.mark.parametrize("stem", sorted(EXPECTED_GRADES), ids=sorted(EXPECTED_GRADES))
def test_expected_table_has_fixture_file(stem: str) -> None:
    """Every expected-grade entry must have a matching JSON fixture."""
    path = Path(__file__).parent / "fixtures" / "revert_standard" / f"{stem}.json"
    assert path.is_file(), f"EXPECTED_GRADES[{stem!r}] has no fixture at {path}"


@pytest.mark.parametrize("fixture_path", _fixture_params())
def test_independent_standard_matches_hardcoded_table(fixture_path: Path) -> None:
    """Hardcoded pins must agree with the independent Revert Standard calculator."""
    payload = load_fixture(fixture_path)
    independent, _cert = compute_standard_grade(payload)
    expected = EXPECTED_GRADES[fixture_path.stem]
    assert independent == expected, (
        f"{fixture_path.stem}: independent standard={independent} "
        f"hardcoded={expected} ({FIXTURE_SECTIONS.get(fixture_path.stem, '?')})"
    )


@pytest.mark.parametrize("fixture_path", _fixture_params(apply_pending_xfail=True))
def test_tool_grade_matches_revert_standard(fixture_path: Path) -> None:
    """Tool scorer must match the Revert Standard expected grade."""
    stem = fixture_path.stem
    expected = EXPECTED_GRADES[stem]
    expected_cert = certification_for_grade(expected)
    health = grade_fixture_with_tool(fixture_path)

    assert health.grade == expected, (
        f"{stem}: tool={health.grade} expected={expected} "
        f"(age_cap={health.age_cap_grade} defect={health.defect_grade} "
        f"multi_factor={health.multi_factor_applied} "
        f"section={FIXTURE_SECTIONS.get(stem, '?')})"
    )
    assert health.certification == expected_cert, (
        f"{stem}: certification={health.certification!r} expected={expected_cert!r}"
    )
    assert health.is_certified == (expected_cert == "true")


@pytest.mark.parametrize(
    "stem,expected",
    [
        ("report_1SHK383Z", "C"),
        ("report_JEHXTXVN", "C"),
        ("report_1SHKKWGZ", "C"),
        ("report_ZC19AACC", "C"),
        ("report_ZAD2AZ2A", "F"),
        ("report_ZAD2AX9T", "F"),
    ],
)
def test_finding8_report_serial_pins(stem: str, expected: str) -> None:
    """Finding 8 report serials are pinned to the gap-analysis expected grades."""
    path = Path(__file__).parent / "fixtures" / "revert_standard" / f"{stem}.json"
    payload = load_fixture(path)
    assert payload.get("serial_number") == stem.removeprefix("report_")
    health = grade_fixture_with_tool(path)
    assert health.grade == expected


def test_agreement_summary(capsys: pytest.CaptureFixture[str]) -> None:
    """Print a one-shot agreement report across all fixtures."""
    rows: list[tuple[str, str, str, str, str]] = []
    agree = 0
    xfail_n = 0
    mismatch = 0

    for path in FIXTURE_PATHS:
        stem = path.stem
        expected = EXPECTED_GRADES[stem]
        independent, _ = compute_standard_grade(load_fixture(path))
        health = grade_fixture_with_tool(path)
        tool = health.grade
        if stem in PENDING_GRADUATED_SCORING and tool != expected:
            status = "xfail"
            xfail_n += 1
        elif tool == expected == independent:
            status = "pass"
            agree += 1
        else:
            status = "FAIL"
            mismatch += 1
        rows.append((stem, expected, independent, tool, status))

    print()
    print("Revert Standard regression harness (#124)")
    print(f"{'fixture':40s} {'exp':3s} {'ind':3s} {'tool':4s} status")
    for stem, expected, independent, tool, status in rows:
        print(f"{stem:40s} {expected:3s} {independent:3s} {tool:4s} {status}")
    print(f"agreement: {agree} pass / {xfail_n} xfail / {mismatch} fail  (n={len(rows)})")

    unexpected = [r for r in rows if r[4] == "FAIL"]
    assert not unexpected, f"unexpected mismatches: {unexpected}"
    assert agree + xfail_n == len(rows)
