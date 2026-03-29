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

import csv
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

# Advanced NVMe table: HTML column that renders modal trigger buttons (not CSV text).
_NVME_HTML_LOGS_HEADER = "NVMe · log viewers (OCP C0h)"


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

    def generate_csv(self, devices: list[dict], output_path: str) -> None:
        """
        Generate a single CSV with union of advanced columns (for spreadsheets / sorting).

        Rows include ``Report category`` plus all column headers used on any tab; cells are
        blank when a column does not apply to that device category.
        """
        enriched = self._enrich_devices(devices)
        headers = self._advanced_csv_headers(enriched)
        rows: list[dict[str, str]] = []
        for d in enriched:
            cat = d.get("report_category", "Other")
            cat_devices = [x for x in enriched if x.get("report_category") == cat]
            specs = self._advanced_column_specs(cat, cat_devices)
            row = {h: "" for h in headers}
            row["Report category"] = str(cat)
            for spec in specs:
                h, fn, mode = self._spec_triple(spec)
                if mode == "html":
                    row[h] = ""
                    continue
                try:
                    val = fn(d)
                except Exception:
                    val = ""
                if val is None:
                    val = ""
                row[h] = str(val)
            for h, fn in ReportGenerator._nvme_csv_json_column_fns(cat, cat_devices):
                if h in row:
                    try:
                        row[h] = str(fn(d))
                    except Exception:
                        row[h] = ""
            rows.append(row)
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

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
        default_tab_slug = _REPORT_TABS[0][1]

        return f"""<!DOCTYPE html>
<html lang="en">
{self._render_report_head(timestamp, palette_css)}
<body data-view="{html.escape(dv)}">
{self._render_json_log_modal()}
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
                    <button type="button" class="mode-btn{self._active_class(dv == "simple")}" data-view="simple">Simple</button>
                    <button type="button" class="mode-btn{self._active_class(dv == "advanced")}" data-view="advanced">Advanced</button>
                </div>
            </div>
        </header>

{self._render_summary_strip(len(devices), healthy, warning, failed)}

{panels_html}

        <footer class="page-foot">
            <p>Generated by CDI Health Scanner</p>
            <p>© {datetime.now().year} Circular Drive Initiative</p>
        </footer>
    </main>
{self._render_report_script(default_tab_slug)}
</body>
</html>"""

    @staticmethod
    def _active_class(active: bool) -> str:
        return " active" if active else ""

    @staticmethod
    def _spec_triple(spec: tuple) -> tuple[str, object, str]:
        if len(spec) >= 3:
            return spec[0], spec[1], spec[2]
        return spec[0], spec[1], "text"

    @staticmethod
    def _render_json_log_modal() -> str:
        return """    <div id="cdi-json-modal" class="cdi-json-modal" hidden>
        <div class="cdi-json-modal__backdrop" data-cdi-json-close="1"></div>
        <div class="cdi-json-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="cdi-json-modal-title">
            <header class="cdi-json-modal__head">
                <h3 class="cdi-json-modal__title" id="cdi-json-modal-title">Log</h3>
                <button type="button" class="cdi-json-modal__close" data-cdi-json-close="1" aria-label="Close">×</button>
            </header>
            <pre class="cdi-json-modal__pre"></pre>
        </div>
    </div>"""

    def _render_report_head(self, timestamp: str, palette_css: str) -> str:
        return f"""<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CDI Health Report — {html.escape(timestamp)}</title>
    <style>
        @import url("https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap");
        {palette_css}
        {self._get_report_layout_css()}
    </style>
</head>"""

    @staticmethod
    def _summary_card(label: str, value: int, variant: str = "") -> str:
        variant_class = f" {variant}" if variant else ""
        return (
            f'<div class="s-card{variant_class}">'
            f'<span class="s-label">{html.escape(label)}</span>'
            f'<span class="s-val">{value}</span>'
            f"</div>"
        )

    def _render_summary_strip(self, total: int, healthy: int, warning: int, failed: int) -> str:
        cards = [
            self._summary_card("Total devices", total),
            self._summary_card("Healthy", healthy, "s-ok"),
            self._summary_card("Warning", warning, "s-warn"),
            self._summary_card("At risk", failed, "s-bad"),
        ]
        return f"""        <section class="summary-strip" aria-label="Fleet summary">
            {"".join(cards)}
        </section>"""

    @staticmethod
    def _render_report_script(default_tab_slug: str) -> str:
        return f"""    <script>
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
        var savedView = localStorage.getItem("cdi-report-view");
        if (savedView === "simple" || savedView === "advanced") setView(savedView);
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

      var initial = "{default_tab_slug}";
      try {{
        var savedTab = localStorage.getItem("cdi-report-tab");
        if (savedTab) initial = savedTab;
      }} catch (e) {{}}

      if (!document.querySelector('.tab-panel[data-panel="' + initial + '"]')) {{
        initial = "{default_tab_slug}";
      }}

      show(initial);

      (function cdiJsonModal() {{
        var modal = document.getElementById("cdi-json-modal");
        if (!modal) return;
        var pre = modal.querySelector(".cdi-json-modal__pre");
        var titleEl = modal.querySelector(".cdi-json-modal__title");
        function openModal(jsonId, title) {{
          var el = document.getElementById(jsonId);
          if (!el) return;
          try {{
            var data = JSON.parse(el.textContent);
            pre.textContent = JSON.stringify(data, null, 2);
          }} catch (err) {{
            pre.textContent = el.textContent;
          }}
          titleEl.textContent = title || "Log";
          modal.hidden = false;
          document.body.style.overflow = "hidden";
        }}
        function closeModal() {{
          modal.hidden = true;
          document.body.style.overflow = "";
        }}
        document.addEventListener("click", function(e) {{
          var btn = e.target.closest(".btn-json-log");
          if (btn) {{
            e.preventDefault();
            openModal(btn.getAttribute("data-json-id"), btn.getAttribute("data-title"));
            return;
          }}
          if (e.target.getAttribute("data-cdi-json-close")) closeModal();
        }});
        document.addEventListener("keydown", function(e) {{
          if (e.key === "Escape" && !modal.hidden) closeModal();
        }});
      }})();
    }})();
    </script>"""

    def _sidebar_link(self, label: str, slug: str, count: int, active: bool = False) -> str:
        badge = f'<span class="tab-count">{count}</span>'
        active_class = self._active_class(active)
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
                    parts.append(f"{d.reason}: {d.value} (threshold: {d.threshold}) [-{d.points}]")
                else:
                    parts.append(f"{d.reason} [-{d.points}]")
            elif isinstance(d, dict):
                parts.append(str(d.get("reason", d)))
            else:
                parts.append(str(d))
        return " | ".join(parts)

    @staticmethod
    def _nvme_health_log_dict(device: dict) -> dict:
        log = device.get("nvme_smart_health_information_log")
        return log if isinstance(log, dict) else {}

    @staticmethod
    def _nvme_log_field(device: dict, key: str) -> str | int | float:
        v = ReportGenerator._nvme_health_log_dict(device).get(key)
        if v is None:
            return "—"
        return v

    @staticmethod
    def _nvme_selftest_current_string(device: dict) -> str:
        log = device.get("nvme_self_test_log")
        if not isinstance(log, dict):
            return "—"
        op = log.get("current_self_test_operation")
        if isinstance(op, dict) and op.get("string"):
            return str(op["string"])
        return "—"

    @staticmethod
    def _format_nested_cell(val) -> str:
        """Format OCP / nested values for table cells."""
        if val is None:
            return "—"
        if isinstance(val, dict | list):
            try:
                return json.dumps(val, ensure_ascii=False, default=str)
            except TypeError:
                return str(val)
        return str(val)

    def _nvme_extended_column_specs(self) -> list[tuple[str, object]]:
        """Per-field columns from ``nvme_smart_health_information_log`` (+ self-test status)."""
        g = ReportGenerator._nvme_log_field
        return [
            ("NVMe data units read", lambda d: g(d, "data_units_read")),
            ("NVMe data units written", lambda d: g(d, "data_units_written")),
            ("NVMe host reads", lambda d: g(d, "host_reads")),
            ("NVMe host writes", lambda d: g(d, "host_writes")),
            ("Controller busy time (min)", lambda d: g(d, "controller_busy_time")),
            ("NVMe power cycles (log)", lambda d: g(d, "power_cycles")),
            ("NVMe POH (log)", lambda d: g(d, "power_on_hours")),
            ("Unsafe shutdowns", lambda d: g(d, "unsafe_shutdowns")),
            ("Error log entries", lambda d: g(d, "num_err_log_entries")),
            ("Warning temp time (min)", lambda d: g(d, "warning_temp_time")),
            ("Critical comp time (min)", lambda d: g(d, "critical_comp_time")),
            ("Self-test current", ReportGenerator._nvme_selftest_current_string),
        ]

    @staticmethod
    def _devices_any_proto(devices: list[dict], proto: str) -> bool:
        return any(d.get("transport_protocol") == proto for d in devices)

    @staticmethod
    def _ata_attr_ids_union(devices: list[dict]) -> list[int]:
        ids: set[int] = set()
        for d in devices:
            if d.get("transport_protocol") != "ATA":
                continue
            attrs = d.get("smart_attributes")
            if not isinstance(attrs, list):
                continue
            for a in attrs:
                if not isinstance(a, dict) or "id" not in a:
                    continue
                try:
                    ids.add(int(a["id"]))
                except (TypeError, ValueError):
                    pass
        return sorted(ids)

    @staticmethod
    def _ata_attr_label(devices: list[dict], attr_id: int) -> str:
        for d in devices:
            if d.get("transport_protocol") != "ATA":
                continue
            attrs = d.get("smart_attributes")
            if not isinstance(attrs, list):
                continue
            for a in attrs:
                if isinstance(a, dict) and a.get("id") == attr_id:
                    name = a.get("name")
                    if name:
                        return str(name)
        return ""

    @staticmethod
    def _ata_smart_attr_cell(device: dict, attr_id: int) -> str:
        if device.get("transport_protocol") != "ATA":
            return "—"
        attrs = device.get("smart_attributes")
        if not isinstance(attrs, list):
            return "—"
        for a in attrs:
            if not isinstance(a, dict) or a.get("id") != attr_id:
                continue
            parts: list[str] = []
            if "value" in a:
                parts.append(f"value={a['value']}")
            if "worst" in a:
                parts.append(f"worst={a['worst']}")
            if "thresh" in a:
                parts.append(f"thresh={a['thresh']}")
            raw = a.get("raw")
            if isinstance(raw, dict):
                rs = raw.get("string")
                if rs is not None:
                    parts.append(f"raw={rs}")
                elif raw.get("value") is not None:
                    parts.append(f"raw={raw['value']}")
            if "when_failed" in a and a.get("when_failed"):
                parts.append(f"when_failed={a['when_failed']}")
            return "; ".join(parts) if parts else "—"
        return "—"

    @staticmethod
    def _scsi_error_counter_paths_union(devices: list[dict]) -> list[str]:
        paths: set[str] = set()
        for d in devices:
            if d.get("transport_protocol") != "SCSI":
                continue
            sa = d.get("smart_attributes")
            if not isinstance(sa, dict):
                continue
            for section, sub in sa.items():
                if not isinstance(sub, dict):
                    continue
                for k in sub.keys():
                    paths.add(f"{section}.{k}")
        return sorted(paths)

    @staticmethod
    def _scsi_error_counter_cell(device: dict, path: str) -> str:
        if device.get("transport_protocol") != "SCSI":
            return "—"
        sa = device.get("smart_attributes")
        if not isinstance(sa, dict):
            return "—"
        section, _, key = path.partition(".")
        if not key:
            return "—"
        sub = sa.get(section)
        if not isinstance(sub, dict):
            return "—"
        return ReportGenerator._format_nested_cell(sub.get(key))

    @staticmethod
    def _nvme_nested_value(val) -> bool:
        return isinstance(val, dict | list)

    @staticmethod
    def _nvme_log_table_blob_key_casefolds() -> frozenset[str]:
        """Top-level NVMe log keys that hold row arrays (use row-count + JSON modal, not cells)."""
        return frozenset(s.casefold() for s in ("table", "entries", "results"))

    @staticmethod
    def _nvme_scalar_keys_union(devices: list[dict], log_attr: str) -> list[str]:
        """Keys in an NVMe log dict whose values are never list/dict across devices (safe table cells)."""
        keys: set[str] = set()
        nested: set[str] = set()
        blob_cf = ReportGenerator._nvme_log_table_blob_key_casefolds()
        for d in devices:
            log = d.get(log_attr)
            if not isinstance(log, dict):
                continue
            for k, v in log.items():
                if isinstance(k, str) and k.casefold() in blob_cf:
                    nested.add(k)
                    continue
                keys.add(k)
                if ReportGenerator._nvme_nested_value(v):
                    nested.add(k)
        return sorted(keys - nested)

    @staticmethod
    def _nvme_log_scalar_cell_value(v) -> str:
        """Single cell for NVMe log scalars; never inline large structures."""
        if v is None:
            return "—"
        if ReportGenerator._nvme_nested_value(v):
            return "—"
        if isinstance(v, str) and len(v) > 240:
            t = v.lstrip()
            if t.startswith(("[", "{")):
                return "—"
        return str(v)

    @staticmethod
    def _nvme_err_log_scalar_field(device: dict, key: str) -> str:
        log = device.get("nvme_error_information_log")
        if not isinstance(log, dict):
            return "—"
        v = log.get(key)
        return ReportGenerator._nvme_log_scalar_cell_value(v)

    @staticmethod
    def _nvme_selftest_scalar_field(device: dict, key: str) -> str:
        log = device.get("nvme_self_test_log")
        if not isinstance(log, dict):
            return "—"
        v = log.get(key)
        return ReportGenerator._nvme_log_scalar_cell_value(v)

    @staticmethod
    def _nvme_error_table_len(device: dict) -> int:
        log = device.get("nvme_error_information_log")
        if not isinstance(log, dict):
            return 0
        for k in ("table", "entries"):
            t = log.get(k)
            if isinstance(t, list):
                return len(t)
        return 0

    @staticmethod
    def _nvme_selftest_table_len(device: dict) -> int:
        log = device.get("nvme_self_test_log")
        if not isinstance(log, dict):
            return 0
        for k in ("table", "entries"):
            t = log.get(k)
            if isinstance(t, list):
                return len(t)
        return 0

    @staticmethod
    def _nvme_ocp_summary(device: dict) -> str:
        o = device.get("ocp_smart_log")
        if not isinstance(o, dict) or not o:
            return "—"
        return f"Yes ({len(o)} fields)"

    @staticmethod
    def _nvme_ocp_keys_union(devices: list[dict]) -> list[str]:
        """Stable union of OCP SMART log (C0h) field names across NVMe devices."""
        keys: set[str] = set()
        for d in devices:
            o = d.get("ocp_smart_log")
            if isinstance(o, dict) and o:
                keys.update(o.keys())
        return sorted(keys)

    @staticmethod
    def _format_ocp_smart_value(val) -> str:
        """Render one OCP field for table/CSV (handles 128-bit hi/lo from nvme-cli JSON)."""
        if val is None:
            return "—"
        if isinstance(val, dict):
            if "hi" in val and "lo" in val:
                try:
                    hi = int(val["hi"]) & 0xFFFFFFFFFFFFFFFF
                    lo = int(val["lo"]) & 0xFFFFFFFFFFFFFFFF
                    return str((hi << 64) | lo)
                except (TypeError, ValueError):
                    pass
            try:
                s = json.dumps(val, ensure_ascii=False, default=str)
            except TypeError:
                s = str(val)
            return s if len(s) <= 200 else s[:197] + "…"
        if isinstance(val, list):
            try:
                s = json.dumps(val, ensure_ascii=False, default=str)
            except TypeError:
                s = str(val)
            return s if len(s) <= 200 else s[:197] + "…"
        return str(val)

    @staticmethod
    def _ocp_smart_field_cell(device: dict, key: str) -> str:
        o = device.get("ocp_smart_log")
        if not isinstance(o, dict):
            return "—"
        return ReportGenerator._format_ocp_smart_value(o.get(key))

    @staticmethod
    def _nvme_row_json_base_id(device: dict, row_index: int) -> str:
        serial = ReportGenerator._serial_label(device)
        safe = "".join(c if c.isalnum() else "_" for c in serial)[:64]
        if not safe.strip("_"):
            safe = "unknown"
        return f"jlog_{row_index}_{safe}"

    @staticmethod
    def _json_script_tag(element_id: str, obj) -> str:
        payload = json.dumps(obj, ensure_ascii=False, default=str)
        payload = payload.replace("<", "\\u003c")
        return f'<script type="application/json" id="{html.escape(element_id)}">{payload}</script>'

    def _nvme_panel_json_scripts(self, devices: list[dict]) -> str:
        parts: list[str] = []
        for idx, d in enumerate(devices):
            if d.get("transport_protocol") != "NVMe":
                continue
            bid = self._nvme_row_json_base_id(d, idx)
            err = d.get("nvme_error_information_log")
            if isinstance(err, dict) and err:
                parts.append(self._json_script_tag(f"{bid}-err", err))
            st = d.get("nvme_self_test_log")
            if isinstance(st, dict) and st:
                parts.append(self._json_script_tag(f"{bid}-st", st))
            ocp = d.get("ocp_smart_log")
            if isinstance(ocp, dict) and ocp:
                parts.append(self._json_script_tag(f"{bid}-ocp", ocp))
        if not parts:
            return ""
        inner = "\n".join(parts)
        return f'<div class="nvme-json-blobs" aria-hidden="true">\n{inner}\n</div>'

    def _panel_includes_nvme_logs(self, title: str, devices: list[dict]) -> bool:
        if title == "NVMe SSD":
            return True
        return title == "Other" and self._devices_any_proto(devices, "NVMe")

    def _nvme_log_buttons_html(self, device: dict, row_index: int) -> str:
        if device.get("transport_protocol") != "NVMe":
            return '<td class="cell-stat cell-nvme-log-btns">—</td>'
        bid = self._nvme_row_json_base_id(device, row_index)
        btns: list[str] = []
        if isinstance(device.get("nvme_error_information_log"), dict) and device["nvme_error_information_log"]:
            eid = html.escape(f"{bid}-err")
            btns.append(
                f'<button type="button" class="btn-json-log" data-json-id="{eid}" '
                f'data-title="NVMe error information log">Error log</button>'
            )
        if isinstance(device.get("nvme_self_test_log"), dict) and device["nvme_self_test_log"]:
            eid = html.escape(f"{bid}-st")
            btns.append(
                f'<button type="button" class="btn-json-log" data-json-id="{eid}" '
                f'data-title="NVMe self-test log">Self-test log</button>'
            )
        if isinstance(device.get("ocp_smart_log"), dict) and device["ocp_smart_log"]:
            eid = html.escape(f"{bid}-ocp")
            btns.append(
                f'<button type="button" class="btn-json-log" data-json-id="{eid}" '
                f'data-title="OCP SMART extended log (C0h)">OCP C0h</button>'
            )
        inner = '<div class="nvme-log-btns">' + "".join(btns) + "</div>" if btns else "—"
        return f'<td class="cell-stat cell-nvme-log-btns">{inner}</td>'

    @staticmethod
    def _nvme_csv_json_column_names(cat: str, cat_devices: list[dict]) -> list[str]:
        if cat == "NVMe SSD":
            return [
                "NVMe error log (full JSON)",
                "NVMe self-test log (full JSON)",
                "OCP SMART C0h (full JSON)",
            ]
        if cat == "Other" and ReportGenerator._devices_any_proto(cat_devices, "NVMe"):
            return [
                "NVMe error log (full JSON)",
                "NVMe self-test log (full JSON)",
                "OCP SMART C0h (full JSON)",
            ]
        return []

    @staticmethod
    def _nvme_csv_json_column_fns(cat: str, cat_devices: list[dict]) -> list[tuple[str, object]]:
        names = ReportGenerator._nvme_csv_json_column_names(cat, cat_devices)
        if not names:
            return []
        return [
            (names[0], ReportGenerator._csv_json_nvme_error_log),
            (names[1], ReportGenerator._csv_json_nvme_selftest_log),
            (names[2], ReportGenerator._csv_json_ocp_log),
        ]

    @staticmethod
    def _csv_json_nvme_error_log(device: dict) -> str:
        if device.get("transport_protocol") != "NVMe":
            return ""
        log = device.get("nvme_error_information_log")
        if not isinstance(log, dict) or not log:
            return ""
        return json.dumps(log, ensure_ascii=False, default=str)

    @staticmethod
    def _csv_json_nvme_selftest_log(device: dict) -> str:
        if device.get("transport_protocol") != "NVMe":
            return ""
        log = device.get("nvme_self_test_log")
        if not isinstance(log, dict) or not log:
            return ""
        return json.dumps(log, ensure_ascii=False, default=str)

    @staticmethod
    def _csv_json_ocp_log(device: dict) -> str:
        if device.get("transport_protocol") != "NVMe":
            return ""
        log = device.get("ocp_smart_log")
        if not isinstance(log, dict) or not log:
            return ""
        return json.dumps(log, ensure_ascii=False, default=str)

    def _base_column_specs(self) -> list[tuple[str, object]]:
        """Columns common to every device type (identity, capacity, cross-protocol health)."""
        cap = self._format_capacity

        def serial(d: dict) -> str:
            return self._serial_label(d)

        def pending(d: dict):
            v = d.get("pending_sectors")
            if v is not None:
                return v
            return d.get("pending_reallocated_sectors", "—")

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
        ]

    @staticmethod
    def _nvme_summary_column_specs() -> list[tuple[str, object]]:
        """NVMe health / endurance fields not covered by the extended health log."""
        return [
            ("NVMe % used", lambda d: d.get("percentage_used", "—")),
            ("Avail spare %", lambda d: d.get("available_spare", "—")),
            ("Critical warning", lambda d: d.get("critical_warning", "—")),
            ("Media errors", lambda d: d.get("media_errors", "—")),
            ("Data written (TB)", lambda d: d.get("data_written_tb", "—")),
            ("NVMe self-test fails", lambda d: d.get("nvme_self_test_failed_count", "—")),
        ]

    @staticmethod
    def _ata_ssd_endurance_column_specs() -> list[tuple[str, object]]:
        return [
            ("SSD % used (ATA)", lambda d: d.get("ssd_percentage_used_endurance", "—")),
        ]

    @staticmethod
    def _devices_any_ata_ssd(devices: list[dict]) -> bool:
        return any(d.get("transport_protocol") == "ATA" and d.get("media_type") == "SSD" for d in devices)

    def _grading_tail_specs(self) -> list[tuple[str, object]]:
        return [
            ("Health score", lambda d: d.get("health_score", "—")),
            ("Grade", lambda d: d.get("health_grade", "—")),
            ("Health status", lambda d: d.get("health_status", "—")),
            ("CDI certified", lambda d: "Yes" if d.get("is_certified") else "No"),
            ("Deductions", lambda d: self._format_deductions_short(d.get("health_deductions"))),
        ]

    def _nvme_supplemental_column_specs(self, devices: list[dict]) -> list[tuple]:
        """NVMe-only: compact scalar log fields, row counts, OCP summary, and HTML log viewers."""
        out: list[tuple] = [
            ("NVMe error log rows", lambda d: ReportGenerator._nvme_error_table_len(d)),
            ("NVMe self-test rows", lambda d: ReportGenerator._nvme_selftest_table_len(d)),
            ("OCP C0h summary", lambda d: ReportGenerator._nvme_ocp_summary(d)),
        ]
        for k in ReportGenerator._nvme_scalar_keys_union(devices, "nvme_error_information_log"):
            label = f"NVMe error log — {k}"
            out.append((label, lambda d, kk=k: ReportGenerator._nvme_err_log_scalar_field(d, kk)))
        for k in ReportGenerator._nvme_scalar_keys_union(devices, "nvme_self_test_log"):
            label = f"NVMe self-test log — {k}"
            out.append((label, lambda d, kk=k: ReportGenerator._nvme_selftest_scalar_field(d, kk)))
        for k in ReportGenerator._nvme_ocp_keys_union(devices):
            label = f"OCP SMART — {k}"
            out.append((label, lambda d, kk=k: ReportGenerator._ocp_smart_field_cell(d, kk)))
        out.append((_NVME_HTML_LOGS_HEADER, lambda d: "", "html"))
        return out

    def _ata_smart_column_specs(self, devices: list[dict]) -> list[tuple[str, object]]:
        if not self._devices_any_proto(devices, "ATA"):
            return []
        out: list[tuple[str, object]] = []
        for aid in self._ata_attr_ids_union(devices):
            name = self._ata_attr_label(devices, aid)
            title = f"SMART attr {aid}" + (f" ({name})" if name else "")
            out.append((title, lambda d, i=aid: ReportGenerator._ata_smart_attr_cell(d, i)))
        return out

    def _scsi_smart_column_specs(self, devices: list[dict]) -> list[tuple[str, object]]:
        if not self._devices_any_proto(devices, "SCSI"):
            return []
        out: list[tuple[str, object]] = []
        for path in self._scsi_error_counter_paths_union(devices):
            label = f"SCSI error log — {path.replace('.', ' › ')}"
            out.append((label, lambda d, p=path: ReportGenerator._scsi_error_counter_cell(d, p)))
        return out

    def _advanced_column_specs(self, category: str, devices: list[dict]):
        """Wide table: base columns plus only fields relevant to this sidebar category / protocol.

        CSV still unions headers across categories via ``_advanced_csv_headers``; each HTML tab
        shows a narrow, protocol-appropriate set of columns.
        """
        base = self._base_column_specs()
        tail = self._grading_tail_specs()

        if category == "NVMe SSD":
            return (
                base
                + self._nvme_summary_column_specs()
                + self._nvme_extended_column_specs()
                + self._nvme_supplemental_column_specs(devices)
                + tail
            )

        if category in ("SATA HDD", "SATA SSD"):
            ata_extra: list[tuple[str, object]] = []
            if category == "SATA SSD":
                ata_extra.extend(self._ata_ssd_endurance_column_specs())
            return base + ata_extra + self._ata_smart_column_specs(devices) + tail

        if category in ("SAS HDD", "SAS SSD"):
            return base + self._scsi_smart_column_specs(devices) + tail

        # Other: include only blocks for protocols actually present
        if category == "Other":
            mid: list[tuple[str, object]] = []
            if self._devices_any_proto(devices, "NVMe"):
                mid.extend(self._nvme_summary_column_specs())
                mid.extend(self._nvme_extended_column_specs())
                mid.extend(self._nvme_supplemental_column_specs(devices))
            if self._devices_any_ata_ssd(devices):
                mid.extend(self._ata_ssd_endurance_column_specs())
            mid.extend(self._ata_smart_column_specs(devices))
            mid.extend(self._scsi_smart_column_specs(devices))
            return base + mid + tail

        return base + tail

    def _advanced_csv_headers(self, enriched: list[dict]) -> list[str]:
        """Stable union of advanced column headers for CSV export."""
        seen_cat: set[str] = set()
        present: list[str] = []
        for d in enriched:
            c = d.get("report_category", "Other")
            if c not in seen_cat:
                seen_cat.add(c)
                present.append(c)
        order = [label for label, _ in _REPORT_TABS] + ["Other"]
        categories = [c for c in order if c in seen_cat] + [c for c in present if c not in order]

        headers: list[str] = ["Report category"]
        seen_h = set(headers)
        for cat in categories:
            cat_devices = [d for d in enriched if d.get("report_category") == cat]
            for spec in self._advanced_column_specs(cat, cat_devices):
                h = spec[0]
                if h not in seen_h:
                    seen_h.add(h)
                    headers.append(h)
            for h in ReportGenerator._nvme_csv_json_column_names(cat, cat_devices):
                if h not in seen_h:
                    seen_h.add(h)
                    headers.append(h)
        return headers

    def _category_panel(self, title: str, slug: str, devices: list[dict], active: bool = False) -> str:
        active_class = self._active_class(active)
        if not devices:
            body = '<p class="empty-cat">No devices in this category.</p>'
        else:
            rows_simple = "".join(self._generate_row_simple(d) for d in devices)
            specs = self._advanced_column_specs(title, devices)
            thead_adv = "".join(
                self._advanced_header_cell_html(ReportGenerator._spec_triple(s)[0], idx == 0)
                for idx, s in enumerate(specs)
            )
            rows_adv = "".join(self._generate_row_advanced(d, specs, row_index=i) for i, d in enumerate(devices))
            nvme_scripts = ""
            if self._panel_includes_nvme_logs(title, devices):
                nvme_scripts = self._nvme_panel_json_scripts(devices)
            body = self._simple_table_html(rows_simple) + self._advanced_table_html(thead_adv, rows_adv, nvme_scripts)

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
        return (
            "<tr>"
            f'<td class="col-serial">{html.escape(self._serial_label(device))}</td>'
            f'<td class="score">{score}</td>'
            f'<td class="{grade_class}">{grade}</td>'
            f'<td class="{status_class}">{html.escape(str(status))}</td>'
            f'<td class="cell-deductions">{html.escape(ded)}</td>'
            "</tr>"
        )

    def _generate_row_advanced(self, device: dict, specs: list, row_index: int = 0) -> str:
        """One row: all SMART / statistics columns."""
        cells = []
        for idx, spec in enumerate(specs):
            header, fn, mode = self._spec_triple(spec)
            if mode == "html":
                if header == _NVME_HTML_LOGS_HEADER:
                    cells.append(self._nvme_log_buttons_html(device, row_index))
                else:
                    cells.append('<td class="cell-stat">—</td>')
                continue
            try:
                raw = fn(device)
            except Exception:
                raw = "—"
            cells.append(self._advanced_cell_html(header, raw, first_col=(idx == 0)))
        return f"<tr>{''.join(cells)}</tr>"

    @staticmethod
    def _display_column_label(header: str) -> str:
        if header == _NVME_HTML_LOGS_HEADER:
            return "Logs (JSON)"
        if header == "NVMe error log rows":
            return "Err rows"
        if header == "NVMe self-test rows":
            return "ST rows"
        if header == "OCP C0h summary":
            return "OCP C0h"
        if header.startswith("SMART attr "):
            compact = header.replace("SMART attr ", "Attr ", 1)
            return compact.replace("_", " ")
        if header.startswith("SCSI error log — "):
            return header.replace("SCSI error log — ", "SCSI ", 1).replace(" › ", " / ")
        if header.startswith("NVMe error log — "):
            return header.replace("NVMe error log — ", "NVMe err ", 1)
        if header.startswith("NVMe self-test log — "):
            return header.replace("NVMe self-test log — ", "Self-test ", 1)
        if header.startswith("OCP SMART — "):
            return "OCP " + header[len("OCP SMART — ") :]
        replacements = {
            "Controller busy time (min)": "Busy min",
            "Warning temp time (min)": "Warn temp min",
            "Critical comp time (min)": "Critical temp min",
            "NVMe data units read": "Data units read",
            "NVMe data units written": "Data units written",
            "NVMe host reads": "Host reads",
            "NVMe host writes": "Host writes",
            "NVMe power cycles (log)": "NVMe power cycles",
            "NVMe POH (log)": "NVMe POH",
            "NVMe self-test fails": "Self-test fails",
            "NVMe % used": "Percent used",
            "SSD % used (ATA)": "Percent used",
            "Temperature °C": "Temp °C",
            "Highest temp °C": "Peak temp °C",
            "Max rated temp °C": "Max rated °C",
        }
        return replacements.get(header, header)

    def _advanced_header_cell_html(self, header: str, first_col: bool = False) -> str:
        title = html.escape(header)
        display = html.escape(self._display_column_label(header))
        classes = "col-head"
        if first_col:
            classes += " col-head--key"
        return f'<th class="{classes}" scope="col" title="{title}">{display}</th>'

    @staticmethod
    def _normalize_display_value(raw) -> tuple[str, str]:
        if raw is None:
            return "—", "is-missing"
        if isinstance(raw, bool):
            return ("Yes" if raw else "No"), "is-bool"

        text = str(raw).strip()
        if text in {"", "-", "—", "None", "Not Reported", "NOT REPORTED"}:
            return "—", "is-missing"
        return text, ""

    def _format_advanced_cell_text(self, header: str, raw) -> tuple[str, str]:
        text, variant = self._normalize_display_value(raw)
        if variant == "is-missing":
            return text, variant
        if header.startswith("SMART attr ") and "; " in text:
            return text.replace("; ", "\n"), "is-multiline"
        return text, variant

    def _advanced_cell_html(self, header: str, raw, first_col: bool = False) -> str:
        text, variant = self._format_advanced_cell_text(header, raw)
        classes = ["cell-stat"]
        if first_col:
            classes.append("col-serial")
        if variant:
            classes.append(f"cell-stat--{variant}")
        class_attr = " ".join(classes)
        return f'<td class="{class_attr}">{html.escape(text)}</td>'

    @staticmethod
    def _simple_table_html(rows_simple: str) -> str:
        return f"""
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

    @staticmethod
    def _advanced_table_html(thead_adv: str, rows_adv: str, after_table: str = "") -> str:
        return f"""
            <div class="table-wrap advanced-only">
                <table class="device-table device-table--wide">
                    <thead><tr>{thead_adv}</tr></thead>
                    <tbody>{rows_adv}</tbody>
                </table>
                {after_table}
            </div>"""

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
        sections = [
            """
        /* Page shell */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: var(--font);
          background: var(--bg);
          color: var(--text);
          display: flex;
          min-height: 100vh;
          line-height: 1.5;
        }
        .main {
          flex: 1;
          padding: 28px 32px 48px;
          max-width: 1360px;
        }
        """,
            """
        /* Sidebar */
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
          gap: 12px;
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
        .tab-title { flex: 1; min-width: 0; }
        .tab-count {
          font-family: var(--mono);
          font-size: 12px;
          background: var(--accent-soft);
          color: var(--accent);
          padding: 2px 8px;
          border-radius: 999px;
          white-space: nowrap;
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
        """,
            """
        /* Header and summary */
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
          box-shadow: 0 1px 3px rgba(0,0,0,.03);
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
        """,
            """
        /* Tables */
        .table-wrap {
          overflow-x: auto;
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          margin-bottom: 24px;
          box-shadow: 0 1px 4px rgba(0,0,0,.04);
        }
        .device-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
          font-family: var(--mono);
        }
        .device-table th,
        .device-table td {
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
        .device-table tbody tr:nth-child(even) { background: rgba(19, 156, 122, 0.035); }
        .device-table tbody tr:hover { background: rgba(92, 146, 121, 0.12); }
        .device-table tbody tr:last-child td { border-bottom: 0; }
        .device-table .score { font-weight: 700; }
        .device-table--wide {
          font-size: 12px;
          min-width: max-content;
        }
        .device-table--wide th {
          white-space: normal;
          min-width: 8.5rem;
          max-width: 12rem;
          line-height: 1.35;
          vertical-align: bottom;
          position: sticky;
          top: 0;
          z-index: 2;
        }
        .device-table--wide .col-head--key {
          min-width: 9rem;
        }
        .device-table--wide .cell-stat {
          max-width: 18rem;
          min-width: 7rem;
          word-break: break-word;
          white-space: pre-wrap;
          vertical-align: top;
          line-height: 1.45;
        }
        /* Keep advanced table rows short unless the cell is explicitly multiline (e.g. SMART attrs). */
        .device-table--wide .cell-stat:not(.cell-stat--is-multiline):not(.cell-nvme-log-btns) {
          display: -webkit-box;
          -webkit-box-orient: vertical;
          -webkit-line-clamp: 8;
          overflow: hidden;
        }
        .device-table--wide td:first-child,
        .device-table--wide th:first-child {
          position: sticky;
          left: 0;
          z-index: 1;
          background: var(--bg-card);
          box-shadow: 2px 0 4px rgba(0,0,0,.06);
        }
        .device-table--wide thead th:first-child {
          z-index: 3;
          background: var(--accent-soft);
        }
        .cell-stat--is-missing {
          color: var(--muted);
          font-style: italic;
        }
        .cell-stat--is-bool {
          font-family: var(--font);
          font-weight: 600;
        }
        .cell-stat--is-multiline {
          line-height: 1.55;
        }
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
        .nvme-json-blobs { display: none !important; }
        .nvme-log-btns {
          display: flex;
          flex-direction: column;
          gap: 6px;
          align-items: flex-start;
        }
        .btn-json-log {
          padding: 6px 10px;
          border-radius: 6px;
          border: 1px solid var(--border);
          background: var(--bg-card);
          color: var(--accent);
          font-size: 11px;
          font-weight: 600;
          cursor: pointer;
          font-family: var(--font);
        }
        .btn-json-log:hover {
          background: var(--accent-soft);
          border-color: var(--accent);
        }
        .cell-nvme-log-btns {
          max-width: 11rem;
          white-space: normal;
          vertical-align: top;
        }
        .cdi-json-modal[hidden] { display: none !important; }
        .cdi-json-modal:not([hidden]) {
          position: fixed;
          inset: 0;
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .cdi-json-modal__backdrop {
          position: absolute;
          inset: 0;
          background: rgba(26, 36, 32, 0.45);
        }
        .cdi-json-modal__dialog {
          position: relative;
          z-index: 1;
          max-width: min(920px, 92vw);
          max-height: 85vh;
          width: 100%;
          background: var(--bg-card);
          border-radius: var(--radius);
          border: 1px solid var(--border);
          box-shadow: 0 16px 48px rgba(0,0,0,0.2);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .cdi-json-modal__head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 12px 16px;
          border-bottom: 1px solid var(--border);
          background: var(--accent-soft);
        }
        .cdi-json-modal__title {
          font-size: 15px;
          margin: 0;
          color: var(--accent-secondary);
          font-family: var(--font);
        }
        .cdi-json-modal__close {
          border: none;
          background: transparent;
          font-size: 22px;
          line-height: 1;
          cursor: pointer;
          color: var(--muted);
          padding: 4px 8px;
          border-radius: 6px;
        }
        .cdi-json-modal__close:hover {
          background: var(--accent-soft-strong);
          color: var(--text);
        }
        .cdi-json-modal__pre {
          margin: 0;
          padding: 16px;
          overflow: auto;
          flex: 1;
          font-family: var(--mono);
          font-size: 12px;
          line-height: 1.45;
          white-space: pre-wrap;
          word-break: break-word;
          color: var(--text);
        }
        """,
            """
        /* Footer and print */
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
        """,
        ]
        return "\n".join(sections)
