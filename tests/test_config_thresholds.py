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

"""Tests that packaged thresholds.yaml keys are consumed by ThresholdConfig."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cdi_health.classes.config import (
    DEFAULT_THRESHOLDS,
    ConfigError,
    ThresholdConfig,
    get_default_config_path,
    validate_thresholds,
)
from cdi_health.classes.scoring import HealthScoreCalculator


def _leaf_paths(node: object, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    """Collect dotted leaf key paths from a nested dict (skip comment-only empties)."""
    if not isinstance(node, dict):
        return {prefix} if prefix else set()
    paths: set[tuple[str, ...]] = set()
    for key, value in node.items():
        path = prefix + (str(key),)
        if isinstance(value, dict):
            paths |= _leaf_paths(value, path)
        else:
            paths.add(path)
    return paths


class TestThresholdsYamlConsumed:
    def test_every_yaml_leaf_is_reachable(self) -> None:
        path = get_default_config_path()
        assert path is not None and path.exists()
        with Path(path).open(encoding="utf-8") as f:
            loaded = yaml.safe_load(f)

        cfg = ThresholdConfig(path)
        # Access every public property that maps to YAML so drift is obvious
        _ = (
            cfg.expected_smart_result,
            cfg.expected_smart_self_test_result,
            cfg.maximum_reallocated_sectors,
            cfg.maximum_pending_sectors,
            cfg.maximum_uncorrectable_errors,
            cfg.maximum_ssd_percentage_used,
            cfg.minimum_ssd_available_spare,
            cfg.ssd_wear_warning_moderate,
            cfg.ssd_wear_warning_high,
            cfg.ssd_wear_moderate_deduction,
            cfg.ssd_wear_high_deduction,
            cfg.nvme_wctt_warning_minutes,
            cfg.nvme_cctt_critical_minutes,
            cfg.ocp_scoring_enabled,
            cfg.ocp_capacitor_health_min,
            cfg.ocp_bad_user_nand_warning,
            cfg.ocp_bad_user_nand_critical,
            cfg.ocp_system_data_used_warning,
            cfg.ocp_incomplete_shutdowns_warning,
            cfg.ocp_thermal_throttle_events_warning,
            cfg.maximum_grown_defects,
            cfg.maximum_scsi_uncorrected_errors,
            cfg.maximum_operating_temperature,
            cfg.warning_temperature,
            cfg.hdd_sector_concern_threshold,
            cfg.hdd_sector_defect_max_deduction_points,
            cfg.hdd_sector_excess_points_per_sector,
            cfg.hdd_sector_excess_cap,
            cfg.grade_score_bands,
            cfg.smart_failure_deduction,
            cfg.per_sector_deduction,
            cfg.threshold_exceeded_deduction,
            cfg.temp_warning_deduction,
            cfg.temp_critical_deduction,
            cfg.grading_profile,
            cfg.age_cap_enabled,
            cfg.selftest_recent_poh_window,
            cfg.grade_band_base_scores,
            cfg.scsi_grown_defects_bands,
            cfg.scsi_uncorrected_errors_bands,
        )

        # Every leaf in the YAML must exist in the merged config dict
        for leaf in _leaf_paths(loaded):
            assert cfg.get(*leaf) is not None, f"YAML key {'/'.join(leaf)} not loaded into config"

    def test_calculator_loads_grade_bands_from_config(self) -> None:
        path = get_default_config_path()
        ThresholdConfig.reset_instance()
        ThresholdConfig.configure(path)
        calc = HealthScoreCalculator()
        assert calc.get_grade(90) == "A"
        assert calc.get_grade(75) == "B"
        assert calc.SMART_FAILURE_DEDUCTION == 50
        ThresholdConfig.reset_instance()


class TestConfigValidation:
    """Explicit configs fail loudly; schema validation (#137)."""

    def test_packaged_yaml_is_valid_and_matches_defaults(self) -> None:
        # Single source of truth: code defaults must not drift from thresholds.yaml.
        path = get_default_config_path()
        with Path(path).open(encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        assert validate_thresholds(loaded) == []
        assert loaded == DEFAULT_THRESHOLDS
        ThresholdConfig(path)  # does not raise

    def test_missing_explicit_config_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="not found"):
            ThresholdConfig(tmp_path / "nope.yaml")

    def test_unparseable_config_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("ata: [unclosed\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="parse"):
            ThresholdConfig(bad)

    def test_unknown_key_raises(self, tmp_path: Path) -> None:
        cfg = tmp_path / "typo.yaml"
        cfg.write_text("ata:\n  maximum_realocated_sectors: 5\n", encoding="utf-8")
        with pytest.raises(ConfigError, match=r"ata\.maximum_realocated_sectors: unknown key"):
            ThresholdConfig(cfg)

    def test_unknown_top_level_section_raises(self) -> None:
        assert validate_thresholds({"nvmee": {}}) == ["nvmee: unknown key"]

    @pytest.mark.parametrize(
        ("config", "fragment"),
        [
            ({"ata": {"maximum_reallocated_sectors": "ten"}}, "expected a number"),
            ({"ata": "strict"}, "expected a mapping"),
            ({"nvme": {"ocp": {"enabled": "yes"}}}, "expected a boolean"),
            ({"grading": {"profile": 3}}, "expected a string"),
            ({"grading": {"profile": "strictest"}}, "unknown profile"),
            ({"grading": {"missing_defect_data_grade_cap": "Z"}}, "must be one of A-F"),
            ({"scsi": {"grown_defects_bands": {"A": 0, "B": 50, "C": 10, "D": 100}}}, "non-monotonic"),
            ({"grading": {"grade_bands": {"A": 50, "B": 75}}}, "non-monotonic"),
            ({"grading": {"age_cap": {"consumer": {"B": 20000, "Q": 1}}}}, "unknown grade"),
            ({"ata": {"pending_sectors_bands": {"A": "zero"}}}, "expected a number"),
        ],
    )
    def test_invalid_values_rejected(self, config: dict, fragment: str) -> None:
        problems = validate_thresholds(config)
        assert problems and any(fragment in p for p in problems), problems
        with pytest.raises(ConfigError):
            ThresholdConfig().load_from_dict(config)

    def test_valid_partial_override_loads(self, tmp_path: Path) -> None:
        cfg = tmp_path / "ok.yaml"
        cfg.write_text("grading:\n  profile: binary\nscsi:\n  maximum_grown_defects: 20.5\n", encoding="utf-8")
        loaded = ThresholdConfig(cfg)
        assert loaded.grading_profile == "binary"
        assert loaded.maximum_grown_defects == 20.5
        assert loaded.maximum_pending_sectors == 10  # default retained

    def test_empty_file_means_defaults(self, tmp_path: Path) -> None:
        cfg = tmp_path / "empty.yaml"
        cfg.write_text("", encoding="utf-8")
        assert ThresholdConfig(cfg).grading_profile == "abcdf"

    def test_failed_configure_keeps_previous_instance(self, tmp_path: Path) -> None:
        from cdi_health.classes.config import configure_thresholds, get_config

        before = get_config()
        with pytest.raises(ConfigError):
            configure_thresholds(tmp_path / "missing.yaml")
        assert get_config() is before

    def test_cli_exits_nonzero_on_bad_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from cdi_health import cli

        mock_dir = Path(__file__).parent.parent / "src" / "cdi_health" / "mock_data"
        monkeypatch.setattr(
            "sys.argv",
            ["cdi-health", "scan", "--mock-data", str(mock_dir), "--config", str(tmp_path / "missing.yaml")],
        )
        assert cli.main() == 2
