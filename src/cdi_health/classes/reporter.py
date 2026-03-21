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
Report Generator for CDI Health

Generates detailed HTML and PDF reports for device health.
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from cdi_health.classes.scoring import HealthScoreCalculator


class ReportGenerator:
    """Generate detailed HTML/PDF health reports."""

    def __init__(self):
        """Initialize the report generator."""
        self.calculator = HealthScoreCalculator()

    def generate_html(self, devices: list[dict], output_path: str) -> None:
        """
        Generate HTML report.

        :param devices: List of device dictionaries
        :param output_path: Output file path
        """
        # Enrich devices with health scores
        enriched = self._enrich_devices(devices)

        # Generate HTML content
        html_content = self._generate_html_content(enriched)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def generate_pdf(self, devices: list[dict], output_path: str) -> None:
        """
        Generate PDF report.

        :param devices: List of device dictionaries
        :param output_path: Output file path
        """
        try:
            from weasyprint import HTML
        except ImportError:
            raise RuntimeError("PDF generation requires weasyprint. Install with: pip install weasyprint")

        # Generate HTML first
        enriched = self._enrich_devices(devices)
        html_content = self._generate_html_content(enriched)

        # Convert to PDF
        HTML(string=html_content).write_pdf(output_path)

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

    def _generate_html_content(self, devices: list[dict]) -> str:
        """Generate HTML content for the report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Count by status
        healthy = sum(1 for d in devices if d["health_score"] >= 75)
        warning = sum(1 for d in devices if 40 <= d["health_score"] < 75)
        failed = sum(1 for d in devices if d["health_score"] < 40)

        # Generate device rows
        device_rows = ""
        for device in devices:
            device_rows += self._generate_device_row(device)

        # Generate device details
        device_details = ""
        for device in devices:
            device_details += self._generate_device_detail(device)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CDI Health Report - {timestamp}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>CDI Health Report</h1>
            <p class="subtitle">Storage Device Health Assessment</p>
            <p class="timestamp">Generated: {timestamp}</p>
        </header>

        <section class="summary">
            <h2>Summary</h2>
            <div class="summary-cards">
                <div class="card">
                    <div class="card-value">{len(devices)}</div>
                    <div class="card-label">Total Devices</div>
                </div>
                <div class="card card-healthy">
                    <div class="card-value">{healthy}</div>
                    <div class="card-label">Healthy</div>
                </div>
                <div class="card card-warning">
                    <div class="card-value">{warning}</div>
                    <div class="card-label">Warning</div>
                </div>
                <div class="card card-failed">
                    <div class="card-value">{failed}</div>
                    <div class="card-label">Failed</div>
                </div>
            </div>
        </section>

        <section class="devices">
            <h2>Device Overview</h2>
            <table class="device-table">
                <thead>
                    <tr>
                        <th>Device</th>
                        <th>Model</th>
                        <th>Serial</th>
                        <th>Protocol</th>
                        <th>Capacity</th>
                        <th>Score</th>
                        <th>Grade</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {device_rows}
                </tbody>
            </table>
        </section>

        <section class="details">
            <h2>Device Details</h2>
            {device_details}
        </section>

        <footer>
            <p>Generated by CDI Health Scanner</p>
            <p>&copy; {datetime.now().year} Circular Drive Initiative</p>
        </footer>
    </div>
</body>
</html>"""

    def _generate_device_row(self, device: dict) -> str:
        """Generate HTML table row for a device."""
        score = device.get("health_score", 0)
        grade = device.get("health_grade", "F")
        status = device.get("health_status", "Unknown")

        grade_class = f"grade-{grade.lower()}"
        status_class = "status-healthy" if score >= 75 else ("status-warning" if score >= 40 else "status-failed")

        return f"""
                    <tr>
                        <td>{html.escape(str(device.get("dut", "-")))}</td>
                        <td>{html.escape(str(device.get("model_number", "-")))}</td>
                        <td>{html.escape(str(device.get("serial_number", "-")))}</td>
                        <td>{html.escape(str(device.get("transport_protocol", "-")))}</td>
                        <td>{self._format_capacity(device.get("capacity"))}</td>
                        <td class="score">{score}</td>
                        <td class="{grade_class}">{grade}</td>
                        <td class="{status_class}">{status}</td>
                    </tr>"""

    def _generate_device_detail(self, device: dict) -> str:
        """Generate detailed section for a device."""
        score = device.get("health_score", 0)
        grade = device.get("health_grade", "F")
        status = device.get("health_status", "Unknown")
        deductions = device.get("health_deductions", [])

        grade_class = f"grade-{grade.lower()}"

        # Generate deductions list
        deductions_html = ""
        if deductions:
            deductions_html = "<h4>Health Deductions</h4><ul class='deductions'>"
            for d in deductions:
                severity_class = f"severity-{d.severity}"
                if d.threshold is not None:
                    msg = f"{d.reason}: {d.value} (threshold: {d.threshold}) [-{d.points} pts]"
                else:
                    msg = f"{d.reason} [-{d.points} pts]"
                deductions_html += f"<li class='{severity_class}'>{html.escape(msg)}</li>"
            deductions_html += "</ul>"
        else:
            deductions_html = "<p class='no-issues'>No health issues detected</p>"

        # Generate metrics table
        metrics = self._get_device_metrics(device)
        metrics_html = "<table class='metrics-table'>"
        for label, value in metrics:
            metrics_html += f"<tr><th>{html.escape(label)}</th><td>{html.escape(str(value))}</td></tr>"
        metrics_html += "</table>"

        return f"""
            <div class="device-detail">
                <div class="device-header">
                    <h3>{html.escape(str(device.get("dut", "Unknown")))}</h3>
                    <span class="score-badge">{score}</span>
                    <span class="grade-badge {grade_class}">{grade}</span>
                </div>
                <div class="device-info">
                    <p><strong>Model:</strong> {html.escape(str(device.get("model_number", "-")))}</p>
                    <p><strong>Serial:</strong> {html.escape(str(device.get("serial_number", "-")))}</p>
                    <p><strong>Protocol:</strong> {html.escape(str(device.get("transport_protocol", "-")))}</p>
                    <p><strong>Capacity:</strong> {self._format_capacity(device.get("capacity"))}</p>
                    <p><strong>CDI Certified:</strong> {"Yes" if device.get("is_certified") else "No"}</p>
                </div>
                <div class="device-metrics">
                    <h4>Device Metrics</h4>
                    {metrics_html}
                </div>
                <div class="device-health">
                    {deductions_html}
                </div>
            </div>"""

    def _get_device_metrics(self, device: dict) -> list[tuple[str, str]]:
        """Get device metrics as label-value pairs."""
        protocol = device.get("transport_protocol", "").upper()

        metrics = [
            ("SMART Status", device.get("smart_status", "-")),
        ]

        if protocol == "ATA":
            metrics.extend(
                [
                    ("Reallocated Sectors", device.get("reallocated_sectors", "-")),
                    ("Pending Sectors", device.get("pending_sectors", "-")),
                    ("Uncorrectable Errors", device.get("uncorrectable_errors", "-")),
                    ("Power On Hours", device.get("power_on_hours", "-")),
                    ("Power Cycles", device.get("power_cycle_count", "-")),
                ]
            )
        elif protocol == "NVME":
            metrics.extend(
                [
                    ("Percentage Used", f"{device.get('percentage_used', '-')}%"),
                    ("Available Spare", f"{device.get('available_spare', '-')}%"),
                    ("Media Errors", device.get("media_errors", "-")),
                    ("Power On Hours", device.get("power_on_hours", "-")),
                    ("Power Cycles", device.get("power_cycle_count", "-")),
                ]
            )
        elif protocol == "SCSI":
            metrics.extend(
                [
                    ("Grown Defects", device.get("grown_defects", "-")),
                    ("Uncorrected Errors", device.get("uncorrected_errors", "-")),
                    ("Power On Hours", device.get("power_on_hours", "-")),
                ]
            )

        metrics.append(("Temperature", f"{device.get('current_temperature', '-')}°C"))

        return metrics

    def _format_capacity(self, capacity) -> str:
        """Format capacity in human-readable form."""
        if capacity is None:
            return "-"

        try:
            bytes_val = int(capacity)
        except (ValueError, TypeError):
            return str(capacity)

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

    def _get_css_styles(self) -> str:
        """Get CSS styles for HTML report."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: linear-gradient(135deg, #2c3e50, #3498db);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }

        header .timestamp {
            margin-top: 15px;
            opacity: 0.8;
            font-size: 0.9em;
        }

        section {
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        h2 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
        }

        .card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid #3498db;
        }

        .card-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #2c3e50;
        }

        .card-label {
            color: #666;
            margin-top: 5px;
        }

        .card-healthy { border-left-color: #27ae60; }
        .card-healthy .card-value { color: #27ae60; }

        .card-warning { border-left-color: #f39c12; }
        .card-warning .card-value { color: #f39c12; }

        .card-failed { border-left-color: #e74c3c; }
        .card-failed .card-value { color: #e74c3c; }

        .device-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }

        .device-table th,
        .device-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }

        .device-table th {
            background: #2c3e50;
            color: white;
            font-weight: 500;
        }

        .device-table tr:hover {
            background: #f5f5f5;
        }

        .device-table .score {
            font-weight: bold;
        }

        .grade-a { color: #27ae60; font-weight: bold; }
        .grade-b { color: #2ecc71; font-weight: bold; }
        .grade-c { color: #f39c12; font-weight: bold; }
        .grade-d { color: #e67e22; font-weight: bold; }
        .grade-f { color: #e74c3c; font-weight: bold; }

        .status-healthy { color: #27ae60; }
        .status-warning { color: #f39c12; }
        .status-failed { color: #e74c3c; }

        .device-detail {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .device-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }

        .device-header h3 {
            flex-grow: 1;
            color: #2c3e50;
        }

        .score-badge {
            background: #2c3e50;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }

        .grade-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            color: white;
        }

        .grade-badge.grade-a { background: #27ae60; }
        .grade-badge.grade-b { background: #2ecc71; }
        .grade-badge.grade-c { background: #f39c12; }
        .grade-badge.grade-d { background: #e67e22; }
        .grade-badge.grade-f { background: #e74c3c; }

        .device-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }

        .device-info p {
            margin: 5px 0;
        }

        .device-metrics h4,
        .device-health h4 {
            color: #2c3e50;
            margin-bottom: 10px;
        }

        .metrics-table {
            width: 100%;
            border-collapse: collapse;
        }

        .metrics-table th,
        .metrics-table td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        .metrics-table th {
            background: #f8f9fa;
            width: 40%;
        }

        .deductions {
            list-style: none;
            padding: 0;
        }

        .deductions li {
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 4px;
            background: #f8f9fa;
        }

        .deductions li.severity-warning {
            background: #fff3cd;
            border-left: 4px solid #f39c12;
        }

        .deductions li.severity-critical {
            background: #f8d7da;
            border-left: 4px solid #e74c3c;
        }

        .no-issues {
            color: #27ae60;
            padding: 10px;
            background: #d4edda;
            border-radius: 4px;
        }

        footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }

        @media print {
            body { background: white; }
            .container { max-width: 100%; }
            section { box-shadow: none; border: 1px solid #ddd; }
        }
        """
