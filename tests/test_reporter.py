#
# Copyright (c) 2026 Circular Drive Initiative.
#
# This file is part of CDI Health.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#

"""Tests for HTML/CSV report generation."""

from __future__ import annotations

from pathlib import Path

from cdi_health.classes.mock import MockDevices
from cdi_health.classes.reporter import ReportGenerator


def test_generate_csv_includes_nvme_columns_and_category(tmp_path: Path, mock_data_dir: Path) -> None:
    """CSV export unions advanced columns; NVMe drives get split health-log fields."""
    devices = MockDevices(
        mock_data_path=str(mock_data_dir),
        ignore_ata=False,
        ignore_nvme=False,
        ignore_scsi=False,
    ).devices
    assert len(devices) > 0

    out = tmp_path / "fleet.csv"
    ReportGenerator().generate_csv(devices, str(out))

    text = out.read_text(encoding="utf-8-sig")
    assert "Report category" in text
    assert "NVMe data units read" in text
    assert "NVMe error log —" in text
    assert "SMART attr" in text
