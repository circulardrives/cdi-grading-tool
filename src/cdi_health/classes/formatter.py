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
Output Formatters for CDI Health

Provides various output formats: table, JSON, CSV, YAML.
"""

from __future__ import annotations

import csv
import io
import json
from abc import ABC, abstractmethod
from typing import Any

from cdi_health.classes.colors import Colors, Symbols
from cdi_health.classes.scoring import HealthScoreCalculator, ScoreDeduction


class BaseFormatter(ABC):
    """Base class for output formatters."""

    @abstractmethod
    def format(self, devices: list[dict]) -> str:
        """
        Format device data for output.

        :param devices: List of device dictionaries
        :return: Formatted string
        """
        pass


class TableFormatter(BaseFormatter):
    """ASCII table output with colors and alerts."""

    # Basic column definitions: (key, header, width, align)
    BASIC_COLUMNS = [
        ("dut", "Device", 10, "left"),
        ("model_number", "Model", 22, "left"),
        ("serial_number", "Serial", 14, "left"),
        ("capacity", "Size", 8, "right"),
        ("health_score", "Score", 5, "center"),
        ("health_grade", "Grade", 5, "center"),
        ("health_status", "Status", 12, "left"),
    ]

    # Detailed column definitions with critical stats
    DETAILED_COLUMNS = [
        ("dut", "Device", 10, "left"),
        ("model_number", "Model", 20, "left"),
        ("serial_number", "Serial", 16, "left"),
        ("firmware_revision", "Firmware", 10, "left"),
        ("capacity", "Size", 10, "right"),
        ("power_on_hours", "POH", 8, "right"),
        ("errors_summary", "Errors", 12, "right"),
        ("percentage_used", "Used%", 7, "right"),
        ("health_score", "Score", 5, "center"),
        ("health_grade", "Grade", 5, "center"),
        ("health_status", "Status", 12, "left"),
    ]

    def __init__(self, show_alerts: bool = True, show_header: bool = True, detailed: bool = False):
        """
        Initialize table formatter.

        :param show_alerts: Show alerts section
        :param show_header: Show header banner
        :param detailed: Show detailed table with critical stats
        """
        self.show_alerts = show_alerts
        self.show_header = show_header
        self.detailed = detailed
        self.calculator = HealthScoreCalculator()
        # Set columns based on mode
        self.COLUMNS = self.DETAILED_COLUMNS if detailed else self.BASIC_COLUMNS

    def format(self, devices: list[dict]) -> str:
        """Format devices as ASCII table."""
        if not devices:
            return "No devices found."

        # Enrich devices with health scores
        enriched = self._enrich_devices(devices)

        lines = []

        # Header banner
        if self.show_header:
            lines.extend(self._format_banner(enriched))
            lines.append("")

        # Table
        lines.extend(self._format_table(enriched))

        # Alerts
        if self.show_alerts:
            alerts = self._collect_alerts(enriched)
            if alerts:
                lines.append("")
                lines.extend(self._format_alerts(alerts))

        # Legend
        lines.append("")
        lines.append(self._format_legend())

        return "\n".join(lines)

    def _enrich_devices(self, devices: list[dict]) -> list[dict]:
        """Add health scores to devices."""
        enriched = []
        for device in devices:
            d = device.copy()
            score = self.calculator.calculate(device)
            d["health_score"] = score.score
            d["health_grade"] = score.grade
            d["health_status"] = score.status
            d["health_deductions"] = score.deductions
            d["is_certified"] = score.is_certified
            enriched.append(d)
        return enriched

    def _format_banner(self, devices: list[dict]) -> list[str]:
        """Format header banner with summary."""
        width = sum(c[2] for c in self.COLUMNS) + len(self.COLUMNS) * 3 + 1

        # Count by status
        healthy = sum(1 for d in devices if d["health_score"] >= 75)
        warning = sum(1 for d in devices if 40 <= d["health_score"] < 75)
        failed = sum(1 for d in devices if d["health_score"] < 40)

        title = "CDI Health Scanner"
        summary = f"Scanned: {len(devices)} devices | Healthy: {healthy} | Warning: {warning} | Failed: {failed}"

        lines = [
            Symbols.BOX_TL + Symbols.BOX_H * (width - 2) + Symbols.BOX_TR,
            Symbols.BOX_V + Colors.bold(title.center(width - 2)) + Symbols.BOX_V,
            Symbols.BOX_VL + Symbols.BOX_H * (width - 2) + Symbols.BOX_VR,
            Symbols.BOX_V + summary.center(width - 2) + Symbols.BOX_V,
            Symbols.BOX_BL + Symbols.BOX_H * (width - 2) + Symbols.BOX_BR,
        ]

        return lines

    def _format_table(self, devices: list[dict]) -> list[str]:
        """Format device table."""
        lines = []

        # Calculate column widths (may need to expand for data)
        widths = []
        for key, header, default_width, _ in self.COLUMNS:
            max_len = max(
                len(header),
                max((len(self._get_display_value(d, key)) for d in devices), default=0),
            )
            widths.append(max(default_width, min(max_len, 30)))

        # Header row
        header_cells = []
        for i, (_, header, _, align) in enumerate(self.COLUMNS):
            header_cells.append(self._align_text(header, widths[i], align))

        sep = Symbols.BOX_V_LIGHT
        lines.append(
            Symbols.BOX_TL_LIGHT
            + Symbols.BOX_HT_LIGHT.join(Symbols.BOX_H_LIGHT * (w + 2) for w in widths)
            + Symbols.BOX_TR_LIGHT
        )
        lines.append(f"{sep} " + f" {sep} ".join(header_cells) + f" {sep}")
        lines.append(
            Symbols.BOX_VL_LIGHT
            + Symbols.BOX_CROSS_LIGHT.join(Symbols.BOX_H_LIGHT * (w + 2) for w in widths)
            + Symbols.BOX_VR_LIGHT
        )

        # Data rows
        for device in devices:
            cells = []
            for i, (key, _, _, align) in enumerate(self.COLUMNS):
                value = self._get_display_value(device, key)
                formatted = self._format_cell(key, value, device)
                cells.append(self._align_text(formatted, widths[i], align))

            lines.append(f"{sep} " + f" {sep} ".join(cells) + f" {sep}")

        # Bottom border
        lines.append(
            Symbols.BOX_BL_LIGHT
            + Symbols.BOX_HB_LIGHT.join(Symbols.BOX_H_LIGHT * (w + 2) for w in widths)
            + Symbols.BOX_BR_LIGHT
        )

        return lines

    def _get_display_value(self, device: dict, key: str) -> str:
        """Get display value for a device field."""
        value = device.get(key)

        if key == "capacity":
            # Try bytes field if capacity is not available
            if value is None:
                value = device.get("bytes")
            return self._format_capacity(value)
        elif key == "power_on_hours":
            return self._format_power_on_hours(value)
        elif key == "errors_summary":
            return self._format_errors_summary(device)
        elif key == "percentage_used":
            return self._format_percentage_used(device)
        elif key == "health_status":
            score = device.get("health_score", 0)
            is_healthy = score >= 75
            return self._format_status_plain(value, is_healthy)
        elif value is None:
            return "-"
        else:
            return str(value)[:30]  # Truncate long values

    def _format_cell(self, key: str, value: str, device: dict) -> str:
        """Format a cell value with colors if applicable."""
        if key == "health_score":
            score = device.get("health_score", 0)
            return Colors.format_score(score)
        elif key == "health_grade":
            grade = device.get("health_grade", "F")
            return Colors.format_grade(grade)
        elif key == "health_status":
            score = device.get("health_score", 0)
            status = device.get("health_status", "Unknown")
            is_healthy = score >= 75
            return Colors.format_status(status, is_healthy)
        else:
            return value

    def _format_status_plain(self, status: str, is_healthy: bool) -> str:
        """Format status without color codes (for width calculation)."""
        if is_healthy:
            icon = Symbols.CHECK
        elif status and status.lower() in ("warning", "fair", "poor"):
            icon = Symbols.WARNING
        else:
            icon = Symbols.CROSS
        return f"{icon} {status}" if status else "-"

    def _format_capacity(self, capacity) -> str:
        """Format capacity in human-readable form."""
        if capacity is None:
            return "-"

        try:
            bytes_val = int(capacity)
        except (ValueError, TypeError):
            return str(capacity)

        # Convert to appropriate unit
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        unit_idx = 0
        value = float(bytes_val)

        while value >= 1000 and unit_idx < len(units) - 1:
            value /= 1000
            unit_idx += 1

        if value >= 100:
            return f"{value:.0f} {units[unit_idx]}"
        elif value >= 10:
            return f"{value:.1f} {units[unit_idx]}"
        else:
            return f"{value:.2f} {units[unit_idx]}"

    def _align_text(self, text: str, width: int, align: str) -> str:
        """Align text within width, accounting for ANSI codes."""
        # Calculate visible length (excluding ANSI codes)
        visible_len = len(self._strip_ansi(text))
        padding = max(0, width - visible_len)

        if align == "left":
            return text + " " * padding
        elif align == "right":
            return " " * padding + text
        else:  # center
            left_pad = padding // 2
            right_pad = padding - left_pad
            return " " * left_pad + text + " " * right_pad

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text."""
        import re

        ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
        return ansi_pattern.sub("", text)

    def _collect_alerts(self, devices: list[dict]) -> list[tuple[str, ScoreDeduction]]:
        """Collect all alerts from devices."""
        alerts = []
        for device in devices:
            device_id = device.get("dut", "unknown")
            deductions = device.get("health_deductions", [])
            for d in deductions:
                if d.severity in ("warning", "critical"):
                    alerts.append((device_id, d))
        return alerts

    def _format_alerts(self, alerts: list[tuple[str, ScoreDeduction]]) -> list[str]:
        """Format alerts section."""
        lines = [Colors.bold("Alerts:")]

        for device_id, deduction in alerts:
            icon = Symbols.severity_icon(deduction.severity)
            color = Colors.severity_color(deduction.severity)

            if deduction.threshold is not None:
                msg = f"{deduction.reason}: {deduction.value} (threshold: {deduction.threshold})"
            else:
                msg = deduction.reason

            line = f"  {Colors.colorize(icon, color)} {device_id}: {msg}"
            lines.append(line)

        return lines

    def _format_power_on_hours(self, hours) -> str:
        """Format power on hours."""
        if hours is None or hours == "Not Reported":
            return "-"
        try:
            hours = int(hours)
            if hours < 24:
                return f"{hours}h"
            elif hours < 8760:  # Less than a year
                days = hours // 24
                return f"{days}d"
            else:
                years = hours / 8760
                if years < 10:
                    return f"{years:.1f}y"
                else:
                    return f"{int(years)}y"
        except (ValueError, TypeError):
            return "-"

    def _format_errors_summary(self, device: dict) -> str:
        """Format error summary: reallocated/pending/uncorrectable/media errors."""
        errors = []
        
        # ATA errors
        reallocated = device.get("reallocated_sectors") or 0
        pending = device.get("pending_sectors") or device.get("pending_reallocated_sectors") or 0
        uncorrectable = device.get("uncorrectable_errors") or device.get("offline_uncorrectable_sectors") or 0
        
        # NVMe errors
        media_errors = device.get("media_errors") or 0
        critical_warning = device.get("critical_warning") or 0
        
        # Build summary
        if reallocated > 0:
            errors.append(f"R:{reallocated}")
        if pending > 0:
            errors.append(f"P:{pending}")
        if uncorrectable > 0:
            errors.append(f"U:{uncorrectable}")
        if media_errors > 0:
            errors.append(f"M:{media_errors}")
        if critical_warning > 0:
            errors.append(f"CW:{critical_warning}")
        
        if errors:
            return ",".join(errors)
        return "0"

    def _format_percentage_used(self, device: dict) -> str:
        """Format percentage used (for NVMe and SATA SSDs)."""
        # Try NVMe percentage_used first
        pct = device.get("percentage_used")
        if pct is not None and pct != "Not Reported":
            try:
                return f"{int(pct)}%"
            except (ValueError, TypeError):
                pass
        
        # Try SSD percentage used endurance (SATA SSDs - vendor-specific)
        pct = device.get("ssd_percentage_used_endurance")
        if pct is not None and pct != "Not Reported" and pct != 0:
            try:
                pct_int = int(pct)
                if 0 <= pct_int <= 100:
                    return f"{pct_int}%"
            except (ValueError, TypeError):
                pass
        
        return "-"

    def _format_legend(self) -> str:
        """Format legend line."""
        return (
            f"Legend: {Colors.green(Symbols.CHECK + ' Healthy')}  "
            f"{Colors.yellow(Symbols.WARNING + ' Warning')}  "
            f"{Colors.red(Symbols.CROSS + ' Failed')}"
        )


class JSONFormatter(BaseFormatter):
    """JSON output for scripting."""

    def __init__(self, indent: int = 2, include_scores: bool = True):
        """
        Initialize JSON formatter.

        :param indent: JSON indentation level
        :param include_scores: Include health score data
        """
        self.indent = indent
        self.include_scores = include_scores
        self.calculator = HealthScoreCalculator()

    def format(self, devices: list[dict]) -> str:
        """Format devices as JSON."""
        if self.include_scores:
            devices = self._enrich_devices(devices)

        return json.dumps(devices, indent=self.indent, default=str)

    def _enrich_devices(self, devices: list[dict]) -> list[dict]:
        """Add health scores to devices."""
        enriched = []
        for device in devices:
            d = device.copy()
            score = self.calculator.calculate(device)
            d.update(score.to_dict())
            enriched.append(d)
        return enriched


class CSVFormatter(BaseFormatter):
    """CSV output for spreadsheets."""

    # Fields to include in CSV
    FIELDS = [
        "dut",
        "model_number",
        "serial_number",
        "transport_protocol",
        "capacity",
        "health_score",
        "health_grade",
        "health_status",
        "is_certified",
        "smart_status",
        "reallocated_sectors",
        "pending_sectors",
        "uncorrectable_errors",
        "current_temperature",
    ]

    def __init__(self, include_scores: bool = True):
        """
        Initialize CSV formatter.

        :param include_scores: Include health score data
        """
        self.include_scores = include_scores
        self.calculator = HealthScoreCalculator()

    def format(self, devices: list[dict]) -> str:
        """Format devices as CSV."""
        if not devices:
            return ""

        if self.include_scores:
            devices = self._enrich_devices(devices)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.FIELDS, extrasaction="ignore")
        writer.writeheader()

        for device in devices:
            writer.writerow(device)

        return output.getvalue()

    def _enrich_devices(self, devices: list[dict]) -> list[dict]:
        """Add health scores to devices."""
        enriched = []
        for device in devices:
            d = device.copy()
            score = self.calculator.calculate(device)
            d["health_score"] = score.score
            d["health_grade"] = score.grade
            d["health_status"] = score.status
            d["is_certified"] = score.is_certified
            enriched.append(d)
        return enriched


class YAMLFormatter(BaseFormatter):
    """YAML output for config tools."""

    def __init__(self, include_scores: bool = True):
        """
        Initialize YAML formatter.

        :param include_scores: Include health score data
        """
        self.include_scores = include_scores
        self.calculator = HealthScoreCalculator()

    def format(self, devices: list[dict]) -> str:
        """Format devices as YAML."""
        try:
            import yaml

            if self.include_scores:
                devices = self._enrich_devices(devices)

            return yaml.dump(devices, default_flow_style=False, sort_keys=False)
        except ImportError:
            return "Error: PyYAML not installed. Install with: pip install pyyaml"

    def _enrich_devices(self, devices: list[dict]) -> list[dict]:
        """Add health scores to devices."""
        enriched = []
        for device in devices:
            d = device.copy()
            score = self.calculator.calculate(device)
            d.update(score.to_dict())
            enriched.append(d)
        return enriched


def get_formatter(format_type: str, **kwargs) -> BaseFormatter:
    """
    Get formatter by type name.

    :param format_type: Format type (table, json, csv, yaml)
    :param kwargs: Additional formatter arguments (e.g., detailed=True for table)
    :return: Formatter instance
    """
    formatters = {
        "table": TableFormatter,
        "json": JSONFormatter,
        "csv": CSVFormatter,
        "yaml": YAMLFormatter,
    }

    formatter_class = formatters.get(format_type.lower())
    if formatter_class is None:
        raise ValueError(f"Unknown format type: {format_type}")

    return formatter_class(**kwargs)
