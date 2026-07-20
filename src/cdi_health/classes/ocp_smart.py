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

"""OCP SMART Additional Log (C0h) helpers for predictive-fail scoring."""

from __future__ import annotations

from typing import Any


def ocp_scalar(value: Any) -> int | None:
    """
    Coerce an OCP C0h field to int.

    nvme-cli may return plain ints or ``{"hi": …, "lo": …}`` 128-bit pairs.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower().startswith("0x"):
            try:
                return int(stripped, 16)
            except ValueError:
                return None
        if stripped.lstrip("-").isdigit():
            return int(stripped)
        return None
    if isinstance(value, dict):
        lo = value.get("lo")
        hi = value.get("hi")
        if lo is None and hi is None:
            return None
        try:
            lo_i = int(lo or 0)
            hi_i = int(hi or 0)
        except (TypeError, ValueError):
            return None
        if hi_i == 0:
            return lo_i
        # Saturate large counters for threshold compares
        if hi_i > 0 and lo_i >= 0:
            return (hi_i << 64) + lo_i if hi_i < 0xFFFF else ((1 << 63) - 1)
        return lo_i
    return None


def ocp_get(ocp: dict, *keys: str) -> int | None:
    """Return the first present OCP field matching any of ``keys``."""
    for key in keys:
        if key in ocp:
            return ocp_scalar(ocp.get(key))
    return None
