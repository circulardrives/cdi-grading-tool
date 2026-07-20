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

import yaml

from cdi_health.classes.config import ThresholdConfig, get_default_config_path
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
