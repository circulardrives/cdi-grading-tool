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
import json
from datetime import datetime
from pathlib import Path

from cdi_health.classes.scoring import HealthScoreCalculator


def _read_asset(name: str) -> str:
    """Load packaged brand asset (palette CSS, logo SVG)."""
    try:
        from importlib import resources

        return (resources.files("cdi_health.assets") / name).read_text(encoding="utf-8")
    except Exception:
        alt = Path(__file__).resolve().parent.parent / "assets" / name
        if alt.is_file():
            return alt.read_text(encoding="utf-8")
        raise FileNotFoundError(f"CDI asset not found: {name}") from None


def _prepare_logo_svg(svg: str) -> str:
    """Strip XML declaration and tag the logo for styling."""
    s = svg.strip()
    if s.startswith("<?xml"):
        s = "\n".join(s.splitlines()[1:]).strip()
    return s.replace(
        "<svg ",
        '<svg class="brand-logo-svg" role="img" aria-label="Circular Drive Initiative logo" ',
        1,
    )


# Primary report tabs (left nav), in display order
_REPORT_TABS: tuple[tuple[str, str], ...] = (
    ("SATA HDD", "sata-hdd"),
    ("SAS HDD", "sas-hdd"),
    ("SATA SSD", "sata-ssd"),
    ("SAS SSD", "sas-ssd"),
    ("NVMe SSD", "nvme-ssd"),
)


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
        enriched = self._enrich_devices(devices)
        html_content = self._generate_html_content(enriched, default_view="simple")
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

        enriched = self._enrich_devices(devices)
        html_content = self._generate_html_content(enriched, default_view="advanced")
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
            d["report_category"] = self._device_report_category(d)
            enriched.append(d)
        return enriched

    @staticmethod
    def _device_report_category(device: dict) -> str:
        """Map a device to a report tab (SATA HDD, SAS HDD, …)."""
        proto = device.get("transport_protocol", "")
        media = device.get("media_type", "")
        link = str(device.get("interface_link", "")).upper()

        if proto == "NVMe":
            return "NVMe SSD"
        if proto == "ATA":
            return "SATA HDD" if media == "HDD" else "SATA SSD"
        if proto == "SCSI":
            if "SAS" in link:
                return "SAS HDD" if media == "HDD" else "SAS SSD"
            if "SATA" in link:
                return "SATA HDD" if media == "HDD" else "SATA SSD"
            return "SAS HDD" if media == "HDD" else "SAS SSD"
        return "Other"

    def _generate_html_content(self, devices: list[dict], default_view: str = "simple") -> str:
        """Generate HTML content for the report.

        :param default_view: ``simple`` (grading-focused) or ``advanced`` (full tables + raw fields).
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dv = default_view if default_view in ("simple", "advanced") else "simple"
        btn_simple_active = " active" if dv == "simple" else ""
        btn_adv_active = " active" if dv == "advanced" else ""

        healthy = sum(1 for d in devices if d["health_score"] >= 75)
        warning = sum(1 for d in devices if 40 <= d["health_score"] < 75)
        failed = sum(1 for d in devices if d["health_score"] < 40)

        by_cat: dict[str, list[dict]] = {label: [] for label, _ in _REPORT_TABS}
        by_cat["Other"] = []
        for d in devices:
            cat = d.get("report_category", "Other")
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(d)

        nav_items = []
        panels = []
        for idx, (label, slug) in enumerate(_REPORT_TABS):
            count = len(by_cat.get(label, []))
            nav_items.append(self._sidebar_link(label, slug, count, active=(idx == 0)))
            panels.append(self._category_panel(label, slug, by_cat.get(label, []), active=(idx == 0)))

        other_devices = by_cat.get("Other", [])
        if other_devices:
            nav_items.append(self._sidebar_link("Other", "other", len(other_devices), active=False))
            panels.append(self._category_panel("Other", "other", other_devices, active=False))

        nav_html = "\n".join(nav_items)
        panels_html = "\n".join(panels)

        palette_css = _read_asset("cdi_brand_palette.css")
        logo_svg = _prepare_logo_svg(_read_asset("CDILogo-01.svg"))

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CDI Health Report — {html.escape(timestamp)}</title>
    <style>
        {palette_css}
        {self._get_report_layout_css()}
    </style>
</head>
<body data-view="{html.escape(dv)}">
    <aside class="sidebar">
        <div class="brand">
            <div class="brand-logo">{logo_svg}</div>
            <div class="brand-text">
                <strong>CDI Health</strong>
                <span>Circular Drive Initiative</span>
            </div>
        </div>
        <nav class="nav-tabs" aria-label="Device categories">
{nav_html}
        </nav>
        <p class="sidebar-foot">Storage health assessment</p>
    </aside>
    <main class="main">
        <header class="hero">
            <div class="hero-top">
                <div>
                    <h1>CDI Health Report</h1>
                    <p class="hero-sub">Offline-friendly report · drives identified by serial number only</p>
                    <p class="hero-time">Generated {html.escape(timestamp)}</p>
                </div>
                <div class="view-mode-bar" role="toolbar" aria-label="Report layout">
                    <span class="view-mode-label">View</span>
                    <button type="button" class="mode-btn{btn_simple_active}" data-view="simple">Simple</button>
                    <button type="button" class="mode-btn{btn_adv_active}" data-view="advanced">Advanced</button>
                </div>
            </div>
        </header>

        <section class="summary-strip" aria-label="Fleet summary">
            <div class="s-card"><span class="s-label">Total devices</span><span class="s-val">{len(devices)}</span></div>
            <div class="s-card s-ok"><span class="s-label">Healthy</span><span class="s-val">{healthy}</span></div>
            <div class="s-card s-warn"><span class="s-label">Warning</span><span class="s-val">{warning}</span></div>
            <div class="s-card s-bad"><span class="s-label">At risk</span><span class="s-val">{failed}</span></div>
        </section>

{panels_html}

        <footer class="page-foot">
            <p>Generated by CDI Health Scanner</p>
            <p>© {datetime.now().year} Circular Drive Initiative</p>
        </footer>
    </main>
    <script>
    (function() {{
      function setView(mode) {{
        if (mode !== "simple" && mode !== "advanced") mode = "simple";
        document.body.setAttribute("data-view", mode);
        document.querySelectorAll(".mode-btn").forEach(function(b) {{
          b.classList.toggle("active", b.getAttribute("data-view") === mode);
        }});
        try {{ localStorage.setItem("cdi-report-view", mode); }} catch (e) {{}}
      }}
      document.querySelectorAll(".mode-btn").forEach(function(btn) {{
        btn.addEventListener("click", function() {{
          setView(btn.getAttribute("data-view"));
        }});
      }});
      try {{
        var v = localStorage.getItem("cdi-report-view");
        if (v === "simple" || v === "advanced") setView(v);
      }} catch (e) {{}}

      var tabs = document.querySelectorAll(".nav-tabs .tab-btn");
      var panels = document.querySelectorAll(".tab-panel");
      function show(slug) {{
        tabs.forEach(function(t) {{
          t.classList.toggle("active", t.getAttribute("data-tab") === slug);
        }});
        panels.forEach(function(p) {{
          p.classList.toggle("active", p.getAttribute("data-panel") === slug);
        }});
        try {{ localStorage.setItem("cdi-report-tab", slug); }} catch (e) {{}}
      }}
      tabs.forEach(function(btn) {{
        btn.addEventListener("click", function(e) {{
          e.preventDefault();
          show(btn.getAttribute("data-tab"));
        }});
      }});
      var initial = "{_REPORT_TABS[0][1]}";
      try {{
        var saved = localStorage.getItem("cdi-report-tab");
        if (saved) initial = saved;
      }} catch (e) {{}}
      if (!document.querySelector('.tab-panel[data-panel="' + initial + '"]')) {{
        initial = "{_REPORT_TABS[0][1]}";
      }}
      show(initial);
    }})();
    </script>
</body>
</html>"""

    def _sidebar_link(self, label: str, slug: str, count: int, active: bool = False) -> str:
        badge = f'<span class="tab-count">{count}</span>'
        active_class = " active" if active else ""
        return f"""            <a href="#" class="tab-btn{active_class}" data-tab="{html.escape(slug)}" data-label="{html.escape(label)}">
                <span class="tab-title">{html.escape(label)}</span>
                {badge}
            </a>"""

    @staticmethod
    def _serial_label(device: dict) -> str:
        """Primary row key for offline reports (no /dev paths)."""
        s = str(device.get("serial_number", "") or "").strip()
        return s if s else "—"

    def _format_deductions_short(self, deductions) -> str:
        """One-line summary for table cells."""
        if not deductions:
            return "—"
        parts = []
        for d in deductions:
            if hasattr(d, "reason") and hasattr(d, "points"):
                if getattr(d, "threshold", None) is not None:
                    parts.append(f"{d.reason}: {d.value} (≤{d.threshold}) [-{d.points}]")
                else:
                    parts.append(f"{d.reason} [-{d.points}]")
            elif isinstance(d, dict):
                parts.append(str(d.get("reason", d)))
            else:
                parts.append(str(d))
        return " | ".join(parts)

    def _advanced_column_specs(self):
        """Wide table: SMART + device statistics + health (serial first, no device paths)."""
        cap = self._format_capacity

        def serial(d: dict) -> str:
            return self._serial_label(d)

        def pending(d: dict):
            v = d.get("pending_sectors")
            if v is not None:
                return v
            return d.get("pending_reallocated_sectors", "—")

        def ocp_json(d: dict) -> str:
            o = d.get("ocp_smart_log")
            if not o:
                return "—"
            try:
                return json.dumps(o, ensure_ascii=False, default=str)
            except TypeError:
                return str(o)

        return [
            ("Serial", serial),
            ("Model", lambda d: d.get("model_number", "—")),
            ("Vendor", lambda d: d.get("vendor", "—")),
            ("Protocol", lambda d: d.get("transport_protocol", "—")),
            ("Interface", lambda d: d.get("interface_link", "—")),
            ("Media", lambda d: d.get("media_type", "—")),
            ("Capacity", lambda d: cap(d.get("capacity") or d.get("bytes"))),
            ("Firmware", lambda d: d.get("firmware_revision", "—")),
            ("Form factor", lambda d: d.get("form_factor", "—")),
            ("Rotation rate", lambda d: d.get("rotation_rate", "—")),
            ("SMART status", lambda d: d.get("smart_status", "—")),
            ("Power-on hours", lambda d: d.get("power_on_hours", "—")),
            ("Power cycles", lambda d: d.get("power_cycle_count", "—")),
            ("Load cycles", lambda d: d.get("load_cycle_count", "—")),
            ("Start/stop count", lambda d: d.get("start_stop_count", "—")),
            ("Temperature °C", lambda d: d.get("current_temperature", "—")),
            ("Highest temp °C", lambda d: d.get("highest_temperature", "—")),
            ("Max rated temp °C", lambda d: d.get("maximum_temperature", "—")),
            ("Reallocated sectors", lambda d: d.get("reallocated_sectors", "—")),
            ("Pending sectors", pending),
            ("Uncorrectable errors", lambda d: d.get("uncorrectable_errors", "—")),
            ("Offline uncorrectable", lambda d: d.get("offline_uncorrectable_sectors", "—")),
            ("SSD % used (ATA)", lambda d: d.get("ssd_percentage_used_endurance", "—")),
            ("NVMe % used", lambda d: d.get("percentage_used", "—")),
            ("Avail spare %", lambda d: d.get("available_spare", "—")),
            ("Critical warning", lambda d: d.get("critical_warning", "—")),
            ("Media errors", lambda d: d.get("media_errors", "—")),
            ("Data written (TB)", lambda d: d.get("data_written_tb", "—")),
            ("NVMe self-test fails", lambda d: d.get("nvme_self_test_failed_count", "—")),
            ("OCP SMART log (JSON)", ocp_json),
            ("Health score", lambda d: d.get("health_score", "—")),
            ("Grade", lambda d: d.get("health_grade", "—")),
            ("Health status", lambda d: d.get("health_status", "—")),
            ("CDI certified", lambda d: "Yes" if d.get("is_certified") else "No"),
            ("Deductions", lambda d: self._format_deductions_short(d.get("health_deductions"))),
        ]

    def _category_panel(self, title: str, slug: str, devices: list[dict], active: bool = False) -> str:
        active_class = " active" if active else ""
        if not devices:
            body = '<p class="empty-cat">No devices in this category.</p>'
        else:
            rows_simple = "".join(self._generate_row_simple(d) for d in devices)
            specs = self._advanced_column_specs()
            thead_adv = "".join(f"<th>{html.escape(h)}</th>" for h, _ in specs)
            rows_adv = "".join(self._generate_row_advanced(d, specs) for d in devices)
            table_simple = f"""
            <div class="table-wrap simple-only">
                <table class="device-table device-table--simple">
                    <thead>
                        <tr>
                            <th>Serial</th>
                            <th>Score</th>
                            <th>Grade</th>
                            <th>Status</th>
                            <th>Deductions</th>
                        </tr>
                    </thead>
                    <tbody>{rows_simple}</tbody>
                </table>
            </div>"""
            table_adv = f"""
            <div class="table-wrap advanced-only">
                <table class="device-table device-table--wide">
                    <thead><tr>{thead_adv}</tr></thead>
                    <tbody>{rows_adv}</tbody>
                </table>
            </div>"""
            body = table_simple + table_adv

        return f"""
        <section class="tab-panel{active_class}" data-panel="{html.escape(slug)}" aria-labelledby="hdr-{html.escape(slug)}">
            <h2 class="cat-head" id="hdr-{html.escape(slug)}">{html.escape(title)}</h2>
            <p class="cat-meta">{len(devices)} drive(s) · rows keyed by serial number</p>
            {body}
        </section>"""

    def _generate_row_simple(self, device: dict) -> str:
        """Grading-focused row (serial + score + deductions summary)."""
        score = device.get("health_score", 0)
        grade = device.get("health_grade", "F")
        status = device.get("health_status", "Unknown")
        grade_class = f"grade-{grade.lower()}"
        status_class = "status-healthy" if score >= 75 else ("status-warning" if score >= 40 else "status-failed")
        ded = self._format_deductions_short(device.get("health_deductions"))
        return f"""
                        <tr>
                            <td class="col-serial">{html.escape(self._serial_label(device))}</td>
                            <td class="score">{score}</td>
                            <td class="{grade_class}">{grade}</td>
                            <td class="{status_class}">{html.escape(str(status))}</td>
                            <td class="cell-deductions">{html.escape(ded)}</td>
                        </tr>"""

    def _generate_row_advanced(self, device: dict, specs: list) -> str:
        """One row: all SMART / statistics columns."""
        cells = []
        for _, fn in specs:
            try:
                raw = fn(device)
            except Exception:
                raw = "—"
            if raw is None:
                raw = "—"
            text = str(raw)
            cells.append(f'<td class="cell-stat">{html.escape(text)}</td>')
        return f"<tr>{''.join(cells)}</tr>"

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
        if value >= 10:
            return f"{value:.1f} {units[unit_idx]}"
        return f"{value:.2f} {units[unit_idx]}"

    def _get_report_layout_css(self) -> str:
        """Layout and components (brand tokens from cdi_brand_palette.css)."""
        return """
        @import url("https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap");
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: var(--font);
          background: var(--bg);
          color: var(--text);
          display: flex;
          min-height: 100vh;
          line-height: 1.5;
        }
        .sidebar {
          width: var(--sidebar-w);
          flex-shrink: 0;
          background: var(--surface-sidebar);
          border-right: 1px solid var(--border);
          display: flex;
          flex-direction: column;
          position: sticky;
          top: 0;
          align-self: flex-start;
          min-height: 100vh;
        }
        .brand {
          padding: 20px 16px;
          border-bottom: 1px solid var(--border);
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 12px;
        }
        .brand-logo {
          width: 100%;
          max-width: 200px;
        }
        .brand-logo-svg {
          display: block;
          width: 100%;
          height: auto;
        }
        .brand-text strong { display: block; font-size: 16px; color: var(--accent-secondary); }
        .brand-text span { font-size: 12px; color: var(--muted); font-weight: 500; }
        .nav-tabs {
          display: flex;
          flex-direction: column;
          padding: 12px 8px;
          gap: 4px;
          flex: 1;
        }
        .nav-tabs .tab-btn {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 14px;
          border-radius: 8px;
          text-decoration: none;
          color: var(--muted);
          font-size: 14px;
          font-weight: 500;
          border: 1px solid transparent;
          transition: background .15s, color .15s, border-color .15s;
        }
        .nav-tabs .tab-btn:hover {
          background: var(--accent-soft);
          color: var(--text);
        }
        .nav-tabs .tab-btn.active {
          background: var(--bg-card);
          color: var(--accent);
          border-color: var(--border);
          box-shadow: 0 1px 3px rgba(0,0,0,.06);
        }
        .tab-count {
          font-family: var(--mono);
          font-size: 12px;
          background: var(--accent-soft);
          color: var(--accent);
          padding: 2px 8px;
          border-radius: 999px;
        }
        .nav-tabs .tab-btn.active .tab-count {
          background: var(--accent);
          color: #fff;
        }
        .sidebar-foot {
          padding: 16px;
          font-size: 11px;
          color: var(--muted);
          border-top: 1px solid var(--border);
        }
        .main {
          flex: 1;
          padding: 28px 32px 48px;
          max-width: 1280px;
        }
        .hero {
          margin-bottom: 24px;
        }
        .hero h1 {
          font-size: 28px;
          font-weight: 700;
          color: var(--accent-secondary);
          letter-spacing: -0.02em;
        }
        .hero-sub { color: var(--muted); margin-top: 6px; font-size: 15px; }
        .hero-time { font-size: 13px; color: var(--muted); margin-top: 8px; font-family: var(--mono); }
        .hero-top {
          display: flex;
          flex-wrap: wrap;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
        }
        .view-mode-bar {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-shrink: 0;
        }
        .view-mode-label {
          font-size: 12px;
          font-weight: 600;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: .06em;
        }
        .mode-btn {
          padding: 8px 16px;
          border-radius: 8px;
          border: 1px solid var(--border);
          background: var(--bg-card);
          color: var(--text);
          font-family: var(--font);
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
        }
        .mode-btn:hover {
          background: var(--accent-soft);
          border-color: var(--accent);
        }
        .mode-btn.active {
          background: var(--accent);
          color: #fff;
          border-color: var(--accent);
        }
        body[data-view="simple"] .advanced-only { display: none !important; }
        body[data-view="advanced"] .simple-only { display: none !important; }
        .summary-strip {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 12px;
          margin-bottom: 28px;
        }
        .s-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 14px 16px;
        }
        .s-label { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
        .s-val { display: block; font-size: 26px; font-weight: 700; font-family: var(--mono); margin-top: 4px; }
        .s-ok .s-val { color: var(--accent); }
        .s-warn .s-val { color: var(--warn); }
        .s-bad .s-val { color: var(--danger); }
        .tab-panel { display: none; }
        .tab-panel.active { display: block; }
        .cat-head {
          font-size: 20px;
          color: var(--accent-secondary);
          margin-bottom: 4px;
          padding-bottom: 8px;
          border-bottom: 2px solid var(--cdi-green-spruce);
        }
        .cat-meta { font-size: 13px; color: var(--muted); margin-bottom: 16px; }
        .empty-cat {
          padding: 24px;
          background: var(--bg-card);
          border: 1px dashed var(--border);
          border-radius: var(--radius);
          color: var(--muted);
          text-align: center;
        }
        .table-wrap {
          overflow-x: auto;
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          margin-bottom: 24px;
        }
        .table-wrap.inner { margin-bottom: 0; }
        .device-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
          font-family: var(--mono);
        }
        .device-table th, .device-table td {
          padding: 10px 12px;
          text-align: left;
          border-bottom: 1px solid var(--border);
        }
        .device-table th {
          background: var(--accent-soft);
          color: var(--accent);
          font-weight: 600;
          font-family: var(--font);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: .04em;
        }
        .device-table tbody tr:hover { background: rgba(92, 146, 121, 0.12); }
        .device-table .score { font-weight: 700; }
        .device-table--wide {
          font-size: 11px;
          min-width: max-content;
        }
        .device-table--wide th {
          white-space: nowrap;
          position: sticky;
          top: 0;
          z-index: 2;
        }
        .device-table--wide .cell-stat {
          max-width: 28rem;
          word-break: break-word;
          white-space: pre-wrap;
          vertical-align: top;
        }
        .device-table--wide td:first-child,
        .device-table--wide th:first-child {
          position: sticky;
          left: 0;
          z-index: 1;
          background: var(--bg-card);
          box-shadow: 2px 0 4px rgba(0,0,0,.06);
        }
        .device-table--wide thead th:first-child { z-index: 3; background: var(--accent-soft); }
        .cell-deductions {
          max-width: 24rem;
          font-size: 12px;
          word-break: break-word;
          vertical-align: top;
        }
        .col-serial { font-weight: 600; }
        .grade-a { color: var(--cdi-foliage-green); font-weight: 700; }
        .grade-b { color: var(--cdi-green-spruce); font-weight: 700; }
        .grade-c { color: var(--warn); font-weight: 700; }
        .grade-d { color: #c65f00; font-weight: 700; }
        .grade-f { color: var(--danger); font-weight: 700; }
        .status-healthy { color: var(--cdi-simply-green); }
        .status-warning { color: var(--warn); }
        .status-failed { color: var(--danger); }
        .page-foot {
          margin-top: 40px;
          padding-top: 20px;
          border-top: 1px solid var(--border);
          text-align: center;
          font-size: 12px;
          color: var(--muted);
        }
        @media print {
          .sidebar { display: none; }
          .main { max-width: 100%; padding: 16px; }
          .tab-panel { display: block !important; page-break-before: always; }
          .tab-panel:first-of-type { page-break-before: auto; }
        }
        @media (max-width: 900px) {
          body { flex-direction: column; }
          .sidebar {
            position: relative;
            width: 100%;
            min-height: unset;
            flex-direction: row;
            flex-wrap: wrap;
            align-items: center;
          }
          .nav-tabs { flex-direction: row; flex-wrap: wrap; width: 100%; }
        }
        """
