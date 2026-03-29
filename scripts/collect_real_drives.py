#!/usr/bin/env python3
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
Developer helper: collect real drive smartctl JSON into src/cdi_health/mock_data.

Prefer the shipped CLI for releases and end users::

    cdi-health export mock -o ./my-mock-bundle
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from cdi_health.classes.mock_export import export_mock_snapshots_to_dir
from cdi_health.cli import scan_devices_real


def main() -> None:
    print("Scanning devices...")
    try:
        devices = scan_devices_real()
    except Exception as e:
        print(f"Error scanning devices: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(devices)} devices\n")

    mock_data_dir = Path(__file__).resolve().parent.parent / "src" / "cdi_health" / "mock_data"

    written, skipped = export_mock_snapshots_to_dir(devices, mock_data_dir, anonymize=True)
    print(f"\n✓ Done! Wrote {written} file(s), skipped {skipped}. Mock data root: {mock_data_dir}")
    if written == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
