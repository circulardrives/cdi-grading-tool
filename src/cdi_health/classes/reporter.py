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

from cdi_health.classes.explain import attach_explanation
from cdi_health.classes.revert import flag_duplicate_serials, is_ungraded, revert_fields
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
                    val = "—"
                if val is None:
                    val = "—"
                # #126: collapse "not applicable" / empty / N/A to the report-wide em dash
                text = str(val).strip()
                if text.casefold() in {"", "-", "—", "n/a", "na", "none", "not applicable", "not reported"}:
                    text = "—"
                row[h] = text
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
        """Add health scores, Revert §13/§15 fields, and grading rationale."""
        enriched = []
        for device in devices:
            score = self.calculator.calculate(device)
            d = attach_explanation(device, score)
            d.update(revert_fields(d, score))
            d["report_category"] = self._device_report_category(d)
            enriched.append(d)
        flag_duplicate_serials(enriched)
        return enriched

    @staticmethod
    def _score_bucket(device: dict) -> str:
        """Classify a drive for the summary strip; UNGRADED never counts as graded."""
        if is_ungraded(device) or device.get("grading_status") == "UNGRADED":
            return "ungraded"
        score = device.get("health_score")
        if score is None:
            return "ungraded"
        try:
            value = int(score)
        except (TypeError, ValueError):
            return "ungraded"
        if value >= 75:
            return "healthy"
        if value >= 40:
            return "warning"
        return "failed"

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

        healthy = sum(1 for d in devices if self._score_bucket(d) == "healthy")
        warning = sum(1 for d in devices if self._score_bucket(d) == "warning")
        failed = sum(1 for d in devices if self._score_bucket(d) in ("failed", "ungraded"))

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
                    <p class="hero-sub">Certification evidence pack · serial-keyed drives · grading rationale included</p>
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
        @import url("https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap");
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

    @staticmethod
    def _format_one_deduction(d) -> str:
        """
        Format a single deduction for display (#119).

        Graduated attribute bands show ``[grade X]`` (worst-attribute-wins),
        not a cosmetic ``[-N]`` that is never subtracted from the score.
        Non-band warnings/fail-gates keep real point values.
        """
        if hasattr(d, "reason") and hasattr(d, "points"):
            # ScoreDeduction.__str__ already prefers [grade X] when set.
            return str(d)
        if isinstance(d, dict):
            reason = d.get("reason") or "Deduction"
            attr_grade = d.get("attribute_grade")
            if attr_grade is not None:
                prefix = f"{reason}: {d['value']}" if d.get("value") is not None else reason
                return f"{prefix} [grade {attr_grade}]"
            if d.get("threshold") is not None:
                return f"{reason}: {d.get('value')} (threshold: {d['threshold']}) [-{d.get('points', 0)}]"
            points = d.get("points")
            if points is not None:
                return f"{reason} [-{points}]"
            return str(reason)
        return str(d)

    def _format_deductions_short(self, deductions) -> str:
        """One-line summary for table cells."""
        if not deductions:
            return "—"
        return " | ".join(self._format_one_deduction(d) for d in deductions)

    @staticmethod
    def _iter_deduction_dicts(deductions) -> list[dict]:
        """Normalize ScoreDeduction objects or dicts for HTML evidence cards."""
        out: list[dict] = []
        if not deductions:
            return out
        for d in deductions:
            if hasattr(d, "reason") and hasattr(d, "points"):
                out.append(
                    {
                        "reason": d.reason,
                        "points": d.points,
                        "severity": getattr(d, "severity", "info"),
                        "field": getattr(d, "field", None),
                        "value": getattr(d, "value", None),
                        "threshold": getattr(d, "threshold", None),
                        "attribute_grade": getattr(d, "attribute_grade", None),
                    }
                )
            elif isinstance(d, dict):
                out.append(d)
        return out

    @staticmethod
    def _badge_html(text: str, variant: str) -> str:
        return f'<span class="badge badge--{html.escape(variant)}">{html.escape(text)}</span>'

    def _grade_badge(self, grade: str) -> str:
        g = (grade or "F").upper()
        if g in ("UNGRADED", "U"):
            return self._badge_html("UNGRADED", "muted")
        variant = {"A": "ok", "B": "ok", "C": "warn", "D": "warn", "F": "bad"}.get(g, "muted")
        return self._badge_html(f"Grade {g}", variant)

    def _status_badge(self, status: str, score: int | None = 0) -> str:
        status_text = str(status or "Unknown")
        if status_text.lower() == "ungraded" or score is None:
            return self._badge_html("Ungraded", "muted")
        try:
            value = int(score)
        except (TypeError, ValueError):
            return self._badge_html(status_text, "muted")
        if value >= 75:
            variant = "ok"
        elif value >= 40:
            variant = "warn"
        else:
            variant = "bad"
        return self._badge_html(status_text, variant)

    def _render_deduction_list(self, deductions) -> str:
        items = self._iter_deduction_dicts(deductions)
        if not items:
            return '<p class="evidence-empty">No score deductions — metrics within policy.</p>'
        lis = []
        for item in items:
            sev = str(item.get("severity") or "info").lower()
            reason = html.escape(str(item.get("reason") or "Deduction"))
            points = item.get("points")
            attr_grade = item.get("attribute_grade")
            detail_bits = []
            if item.get("field"):
                detail_bits.append(f"field={item['field']}")
            if item.get("value") is not None:
                detail_bits.append(f"value={item['value']}")
            if item.get("threshold") is not None:
                detail_bits.append(f"threshold={item['threshold']}")
            # Graduated bands: show band grade, not a misleading point delta (#119).
            if attr_grade is not None:
                meta = f" (grade {html.escape(str(attr_grade))})"
            elif points is not None:
                meta = f" (−{html.escape(str(points))})"
            else:
                meta = ""
            detail = (
                f'<span class="deduction-meta">{html.escape(" · ".join(detail_bits))}</span>' if detail_bits else ""
            )
            lis.append(
                f'<li class="deduction deduction--{html.escape(sev)}">'
                f'<span class="deduction-sev">{html.escape(sev)}</span>'
                f'<span class="deduction-body"><strong>{reason}</strong>{meta}{detail}</span>'
                f"</li>"
            )
        return f'<ul class="deduction-list">{"".join(lis)}</ul>'

    def _evidence_card_html(self, device: dict) -> str:
        """Per-drive evidence card for simple view (certification rationale + deductions)."""
        score = device.get("health_score")
        grade = device.get("final_grade") or device.get("health_grade", "F")
        status = device.get("health_status", "Unknown")
        serial = self._serial_label(device)
        model = str(device.get("model_number") or "—")
        firmware = str(device.get("firmware_revision") or "—")
        certified = bool(device.get("is_certified"))
        rationale = str(device.get("certification_rationale") or "—")
        score_display = "—" if score is None else score
        score_for_badge = score if isinstance(score, int) else None
        ungraded = is_ungraded(device) or str(grade).upper() in ("UNGRADED", "U")
        if ungraded:
            cert_badge = self._badge_html("Not graded", "muted")
        else:
            cert_badge = self._badge_html("Certified", "ok") if certified else self._badge_html("Not certified", "bad")
        flags = device.get("warning_flags") or []
        reasons = device.get("ungraded_reasons") or []
        extra_bits = []
        if reasons:
            extra_bits.append(
                '<div class="evidence-rationale"><h4>Ungraded reasons</h4>'
                f"<p>{html.escape(' | '.join(str(r) for r in reasons))}</p></div>"
            )
        if flags:
            extra_bits.append(
                '<div class="evidence-rationale"><h4>Warning flags</h4>'
                f"<p>{html.escape(' | '.join(str(f) for f in flags))}</p></div>"
            )
        extra_html = "".join(extra_bits)
        return f"""
            <article class="evidence-card">
              <header class="evidence-card__head">
                <div>
                  <h3 class="evidence-card__title">{html.escape(serial)}</h3>
                  <p class="evidence-card__sub">{html.escape(model)} · FW {html.escape(firmware)}</p>
                </div>
                <div class="evidence-card__badges">
                  {self._grade_badge(str(grade))}
                  {self._status_badge(str(status), score_for_badge)}
                  {cert_badge}
                </div>
              </header>
              <dl class="evidence-metrics">
                <div><dt>Score</dt><dd class="mono">{html.escape(str(score_display))}</dd></div>
                <div><dt>Protocol</dt><dd>{html.escape(str(device.get("transport_protocol") or "—"))}</dd></div>
                <div><dt>Capacity</dt><dd>{html.escape(self._format_capacity(device.get("bytes") or device.get("capacity")))}</dd></div>
                <div><dt>POH</dt><dd class="mono">{html.escape(str(device.get("power_on_hours") if device.get("power_on_hours") is not None else "—"))}</dd></div>
              </dl>
              <div class="evidence-rationale">
                <h4>Certification rationale</h4>
                <p>{html.escape(rationale)}</p>
              </div>
              {extra_html}
              <div class="evidence-deductions">
                <h4>Grading deductions</h4>
                {self._render_deduction_list(device.get("health_deductions"))}
              </div>
            </article>"""

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
        text = str(val).strip()
        # #126: SCSI verify-log "not applicable" and empty cells use the report em dash
        if text.casefold() in {"", "-", "—", "n/a", "na", "none", "not applicable", "not reported"}:
            return "—"
        return text

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
            ("Non-medium errors", lambda d: d.get("non_medium_errors", "—")),
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
        def _join_list(key: str):
            def _fn(d: dict):
                values = d.get(key) or []
                if not values:
                    return "—"
                return " | ".join(str(v) for v in values)

            return _fn

        return [
            ("Health score", lambda d: d.get("health_score", "—")),
            ("Grade", lambda d: d.get("final_grade") or d.get("health_grade", "—")),
            ("Health status", lambda d: d.get("health_status", "—")),
            ("Grading status", lambda d: d.get("grading_status", "—")),
            ("Ungraded reasons", _join_list("ungraded_reasons")),
            ("Warning flags", _join_list("warning_flags")),
            ("Fail reason codes", _join_list("fail_reason_codes")),
            ("Age-cap grade", lambda d: d.get("age_cap_grade", "—")),
            ("Defect grade", lambda d: d.get("defect_grade", "—")),
            ("Multi-factor applied", lambda d: d.get("multi_factor_applied", "—")),
            ("Revert eligible", lambda d: d.get("revert_eligible", "—")),
            ("Revert certified", lambda d: d.get("revert_certified", "—")),
            ("Recommended use", lambda d: d.get("recommended_use", "—")),
            ("Drive class", lambda d: d.get("drive_class", "—")),
            ("Scan timestamp", lambda d: d.get("scan_timestamp", "—")),
            ("Revert standard version", lambda d: d.get("revert_standard_version", "—")),
            ("CDI certified", lambda d: "Yes" if d.get("is_certified") else "No"),
            ("Certification rationale", lambda d: d.get("certification_rationale", "—")),
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
            evidence = "".join(self._evidence_card_html(d) for d in devices)
            specs = self._advanced_column_specs(title, devices)
            thead_adv = "".join(
                self._advanced_header_cell_html(ReportGenerator._spec_triple(s)[0], idx == 0)
                for idx, s in enumerate(specs)
            )
            rows_adv = "".join(self._generate_row_advanced(d, specs, row_index=i) for i, d in enumerate(devices))
            nvme_scripts = ""
            if self._panel_includes_nvme_logs(title, devices):
                nvme_scripts = self._nvme_panel_json_scripts(devices)
            body = (
                self._simple_table_html(rows_simple)
                + f'<div class="evidence-grid simple-only">{evidence}</div>'
                + self._advanced_table_html(thead_adv, rows_adv, nvme_scripts)
            )

        return f"""
        <section class="tab-panel{active_class}" data-panel="{html.escape(slug)}" aria-labelledby="hdr-{html.escape(slug)}">
            <h2 class="cat-head" id="hdr-{html.escape(slug)}">{html.escape(title)}</h2>
            <p class="cat-meta">{len(devices)} drive(s) · serial-keyed summary · per-drive evidence below</p>
            {body}
        </section>"""

    def _generate_row_simple(self, device: dict) -> str:
        """Grading-focused row (serial + score + grade badge)."""
        score = device.get("health_score")
        grade = device.get("final_grade") or device.get("health_grade", "F")
        status = device.get("health_status", "Unknown")
        model = str(device.get("model_number") or "—")
        score_display = "—" if score is None else score
        score_for_badge = score if isinstance(score, int) else None
        return (
            "<tr>"
            f'<td class="col-serial">{html.escape(self._serial_label(device))}</td>'
            f"<td>{html.escape(model)}</td>"
            f'<td class="score mono">{html.escape(str(score_display))}</td>'
            f"<td>{self._grade_badge(str(grade))}</td>"
            f"<td>{self._status_badge(str(status), score_for_badge)}</td>"
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
    def _format_scalar_for_display(raw) -> str:
        """Coerce smartctl-style objects to readable table text."""
        if isinstance(raw, dict):
            for key in ("string", "name"):
                val = raw.get(key)
                if val not in (None, ""):
                    return str(val).strip()
            if set(raw.keys()) == {"value"}:
                return str(raw["value"]).strip()
            try:
                s = json.dumps(raw, ensure_ascii=False, default=str)
            except TypeError:
                s = str(raw)
            return s if len(s) <= 200 else s[:197] + "…"
        if isinstance(raw, list):
            try:
                s = json.dumps(raw, ensure_ascii=False, default=str)
            except TypeError:
                s = str(raw)
            return s if len(s) <= 200 else s[:197] + "…"
        return str(raw).strip()

    @staticmethod
    def _normalize_display_value(raw) -> tuple[str, str]:
        if raw is None:
            return "—", "is-missing"
        if isinstance(raw, bool):
            return ("Yes" if raw else "No"), "is-bool"

        text = ReportGenerator._format_scalar_for_display(raw)
        if text.casefold() in {
            "",
            "-",
            "—",
            "none",
            "n/a",
            "na",
            "not reported",
            "not applicable",
        }:
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
        if variant == "is-multiline":
            inner = f'<span class="cell-stat__body">{html.escape(text)}</span>'
        else:
            inner = f'<span class="cell-stat__clamp">{html.escape(text)}</span>'
        return f'<td class="{class_attr}">{inner}</td>'

    @staticmethod
    def _simple_table_html(rows_simple: str) -> str:
        return f"""
            <div class="table-wrap simple-only">
                <table class="device-table device-table--simple">
                    <thead>
                        <tr>
                            <th>Serial</th>
                            <th>Model</th>
                            <th>Score</th>
                            <th>Grade</th>
                            <th>Status</th>
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
        """Layout/components — shadcn-aligned, tokens from cdi_brand_palette.css."""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: var(--font);
          background: var(--background);
          color: var(--foreground);
          display: flex;
          min-height: 100vh;
          line-height: 1.5;
          -webkit-font-smoothing: antialiased;
        }
        .mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }
        .main { flex: 1; padding: 1.75rem 2rem 3rem; max-width: 72rem; min-width: 0; }

        /* Sidebar (shadcn Sidebar-like) */
        .sidebar {
          width: var(--sidebar-w);
          flex-shrink: 0;
          background: var(--sidebar);
          color: var(--sidebar-foreground);
          border-right: 1px solid var(--sidebar-border);
          display: flex;
          flex-direction: column;
          position: sticky;
          top: 0;
          align-self: flex-start;
          min-height: 100vh;
        }
        .brand {
          padding: 1rem 1rem 0.875rem;
          border-bottom: 1px solid var(--sidebar-border);
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }
        .brand-logo { width: 100%; max-width: 11rem; }
        .brand-logo-svg { display: block; width: 100%; height: auto; }
        .brand-text strong { display: block; font-size: 0.9375rem; font-weight: 600; color: var(--foreground); }
        .brand-text span { font-size: 0.75rem; color: var(--muted-foreground); font-weight: 500; }
        .nav-tabs {
          display: flex;
          flex-direction: column;
          padding: 0.5rem;
          gap: 0.125rem;
          flex: 1;
        }
        .nav-tabs .tab-btn {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.75rem;
          padding: 0.5rem 0.75rem;
          border-radius: calc(var(--radius) - 2px);
          text-decoration: none;
          color: var(--sidebar-foreground);
          font-size: 0.875rem;
          font-weight: 500;
          border: none;
          background: transparent;
          transition: background .15s, color .15s;
        }
        .nav-tabs .tab-btn:hover { background: var(--sidebar-accent); color: var(--sidebar-accent-foreground); }
        .nav-tabs .tab-btn.active {
          background: var(--sidebar-accent);
          color: var(--sidebar-primary);
          font-weight: 600;
        }
        .tab-title { flex: 1; min-width: 0; }
        .tab-count {
          font-family: var(--mono);
          font-size: 0.6875rem;
          background: var(--muted);
          color: var(--muted-foreground);
          padding: 0.125rem 0.5rem;
          border-radius: 999px;
          white-space: nowrap;
        }
        .nav-tabs .tab-btn.active .tab-count {
          background: var(--primary);
          color: var(--primary-foreground);
        }
        .sidebar-foot {
          padding: 0.75rem 1rem;
          font-size: 0.6875rem;
          color: var(--muted-foreground);
          border-top: 1px solid var(--sidebar-border);
        }

        /* Hero + view toggle */
        .hero { margin-bottom: 1.5rem; }
        .hero h1 {
          font-size: 1.5rem;
          font-weight: 600;
          letter-spacing: -0.025em;
          color: var(--foreground);
        }
        .hero-sub { color: var(--muted-foreground); margin-top: 0.25rem; font-size: 0.9375rem; }
        .hero-time {
          font-size: 0.8125rem;
          color: var(--muted-foreground);
          margin-top: 0.5rem;
          font-family: var(--mono);
        }
        .hero-top {
          display: flex;
          flex-wrap: wrap;
          align-items: flex-start;
          justify-content: space-between;
          gap: 1rem;
        }
        .view-mode-bar {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          padding: 0.25rem;
          background: var(--muted);
          border-radius: var(--radius);
        }
        .view-mode-label {
          font-size: 0.6875rem;
          font-weight: 500;
          color: var(--muted-foreground);
          padding: 0 0.5rem;
        }
        .mode-btn {
          padding: 0.375rem 0.75rem;
          border-radius: calc(var(--radius) - 2px);
          border: none;
          background: transparent;
          color: var(--muted-foreground);
          font-family: var(--font);
          font-size: 0.8125rem;
          font-weight: 500;
          cursor: pointer;
        }
        .mode-btn:hover { color: var(--foreground); }
        .mode-btn.active {
          background: var(--card);
          color: var(--foreground);
          box-shadow: 0 1px 2px rgba(0,0,0,.06);
        }
        body[data-view="simple"] .advanced-only { display: none !important; }
        body[data-view="advanced"] .simple-only { display: none !important; }

        /* Summary cards */
        .summary-strip {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
          gap: 0.75rem;
          margin-bottom: 1.75rem;
        }
        .s-card {
          background: var(--card);
          color: var(--card-foreground);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 1rem 1.125rem;
        }
        .s-label {
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--muted-foreground);
        }
        .s-val {
          display: block;
          font-size: 1.5rem;
          font-weight: 600;
          font-family: var(--mono);
          margin-top: 0.25rem;
          letter-spacing: -0.02em;
        }
        .s-ok .s-val { color: var(--primary); }
        .s-warn .s-val { color: var(--warn); }
        .s-bad .s-val { color: var(--destructive); }

        .tab-panel { display: none; }
        .tab-panel.active { display: block; }
        .cat-head {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--foreground);
          margin-bottom: 0.25rem;
        }
        .cat-meta { font-size: 0.8125rem; color: var(--muted-foreground); margin-bottom: 1rem; }
        .empty-cat {
          padding: 2rem;
          background: var(--card);
          border: 1px dashed var(--border);
          border-radius: var(--radius);
          color: var(--muted-foreground);
          text-align: center;
          font-size: 0.875rem;
        }

        /* Badges (shadcn Badge-like) */
        .badge {
          display: inline-flex;
          align-items: center;
          border-radius: 999px;
          padding: 0.125rem 0.625rem;
          font-size: 0.75rem;
          font-weight: 500;
          line-height: 1.25rem;
          border: 1px solid transparent;
          white-space: nowrap;
        }
        .badge--ok { background: var(--primary-soft); color: var(--cdi-foliage-green); }
        .badge--warn { background: var(--warn-soft); color: #a16207; }
        .badge--bad { background: var(--danger-soft); color: var(--destructive); }
        .badge--muted { background: var(--muted); color: var(--muted-foreground); }

        /* Evidence cards (simple view) */
        .evidence-grid {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        .evidence-card {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 1.25rem;
        }
        .evidence-card__head {
          display: flex;
          flex-wrap: wrap;
          align-items: flex-start;
          justify-content: space-between;
          gap: 0.75rem;
          margin-bottom: 1rem;
        }
        .evidence-card__title {
          font-size: 1rem;
          font-weight: 600;
          font-family: var(--mono);
          letter-spacing: -0.01em;
        }
        .evidence-card__sub {
          font-size: 0.8125rem;
          color: var(--muted-foreground);
          margin-top: 0.125rem;
        }
        .evidence-card__badges { display: flex; flex-wrap: wrap; gap: 0.375rem; }
        .evidence-metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
          gap: 0.75rem;
          margin-bottom: 1rem;
          padding: 0.875rem;
          background: var(--muted);
          border-radius: calc(var(--radius) - 2px);
        }
        .evidence-metrics dt {
          font-size: 0.6875rem;
          font-weight: 500;
          color: var(--muted-foreground);
        }
        .evidence-metrics dd { font-size: 0.875rem; font-weight: 500; margin-top: 0.125rem; }
        .evidence-rationale, .evidence-deductions { margin-top: 1rem; }
        .evidence-rationale h4, .evidence-deductions h4 {
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--muted-foreground);
          margin-bottom: 0.375rem;
        }
        .evidence-rationale p { font-size: 0.875rem; line-height: 1.55; }
        .evidence-empty { font-size: 0.8125rem; color: var(--muted-foreground); }
        .deduction-list { list-style: none; display: flex; flex-direction: column; gap: 0.5rem; }
        .deduction {
          display: flex;
          gap: 0.625rem;
          align-items: flex-start;
          padding: 0.625rem 0.75rem;
          border-radius: calc(var(--radius) - 2px);
          border: 1px solid var(--border);
          background: var(--background);
          font-size: 0.8125rem;
        }
        .deduction-sev {
          flex-shrink: 0;
          font-size: 0.6875rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          padding: 0.125rem 0.375rem;
          border-radius: 0.25rem;
        }
        .deduction--critical .deduction-sev { background: var(--danger-soft); color: var(--destructive); }
        .deduction--warning .deduction-sev { background: var(--warn-soft); color: #a16207; }
        .deduction--info .deduction-sev { background: var(--muted); color: var(--muted-foreground); }
        .deduction-body { min-width: 0; }
        .deduction-meta {
          display: block;
          margin-top: 0.25rem;
          font-family: var(--mono);
          font-size: 0.6875rem;
          color: var(--muted-foreground);
        }

        /* Tables (shadcn Table-like) */
        .table-wrap {
          overflow-x: auto;
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          margin-bottom: 1.5rem;
        }
        .device-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
        }
        .device-table th,
        .device-table td {
          padding: 0.75rem 1rem;
          text-align: left;
          border-bottom: 1px solid var(--border);
          height: 3rem;
          vertical-align: middle;
        }
        .device-table th {
          background: transparent;
          color: var(--muted-foreground);
          font-weight: 500;
          font-family: var(--font);
          font-size: 0.75rem;
          text-transform: none;
          letter-spacing: 0;
          height: 2.75rem;
        }
        .device-table tbody tr:hover { background: color-mix(in srgb, var(--muted) 50%, transparent); }
        .device-table tbody tr:last-child td { border-bottom: 0; }
        .device-table .score { font-weight: 600; font-family: var(--mono); }
        .device-table--simple td { font-size: 0.875rem; }
        .device-table--wide { font-size: 0.75rem; font-family: var(--mono); min-width: max-content; }
        .device-table--wide th {
          white-space: normal;
          min-width: 8.5rem;
          max-width: 12rem;
          line-height: 1.35;
          vertical-align: bottom;
          position: sticky;
          top: 0;
          z-index: 2;
          background: var(--card);
        }
        .device-table--wide .col-head--key { min-width: 9rem; }
        .device-table--wide .cell-stat {
          max-width: 18rem;
          min-width: 7rem;
          vertical-align: top;
          height: auto;
          padding-top: 0.625rem;
          padding-bottom: 0.625rem;
        }
        .device-table--wide .cell-stat__clamp {
          display: -webkit-box;
          -webkit-box-orient: vertical;
          -webkit-line-clamp: 8;
          overflow: hidden;
          word-break: break-word;
          white-space: pre-wrap;
          line-height: 1.45;
        }
        .device-table--wide .cell-stat__body {
          display: block;
          word-break: break-word;
          white-space: pre-wrap;
          line-height: 1.55;
        }
        .device-table--wide td:first-child,
        .device-table--wide th:first-child {
          position: sticky;
          left: 0;
          z-index: 1;
          background: var(--card);
          box-shadow: 2px 0 4px rgba(0,0,0,.04);
        }
        .device-table--wide thead th:first-child { z-index: 3; }
        .cell-stat--is-missing { color: var(--muted-foreground); font-style: italic; }
        .cell-stat--is-bool { font-family: var(--font); font-weight: 600; }
        .cell-stat--is-multiline { line-height: 1.55; }
        .cell-deductions {
          max-width: 24rem;
          font-size: 0.75rem;
          word-break: break-word;
          vertical-align: top;
        }
        .col-serial { font-weight: 600; font-family: var(--mono); }
        .grade-a, .grade-b { color: var(--cdi-foliage-green); font-weight: 600; }
        .grade-c { color: var(--warn); font-weight: 600; }
        .grade-d { color: #c65f00; font-weight: 600; }
        .grade-f { color: var(--destructive); font-weight: 600; }
        .status-healthy { color: var(--primary); }
        .status-warning { color: var(--warn); }
        .status-failed { color: var(--destructive); }

        .nvme-json-blobs { display: none !important; }
        .nvme-log-btns { display: flex; flex-direction: column; gap: 0.375rem; align-items: flex-start; }
        .btn-json-log {
          padding: 0.375rem 0.625rem;
          border-radius: calc(var(--radius) - 2px);
          border: 1px solid var(--border);
          background: var(--card);
          color: var(--foreground);
          font-size: 0.6875rem;
          font-weight: 500;
          cursor: pointer;
          font-family: var(--font);
        }
        .btn-json-log:hover { background: var(--muted); }
        .cell-nvme-log-btns { max-width: 11rem; white-space: normal; vertical-align: top; }

        .cdi-json-modal[hidden] { display: none !important; }
        .cdi-json-modal:not([hidden]) {
          position: fixed;
          inset: 0;
          z-index: 50;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .cdi-json-modal__backdrop {
          position: absolute;
          inset: 0;
          background: rgba(28, 25, 23, 0.5);
        }
        .cdi-json-modal__dialog {
          position: relative;
          z-index: 1;
          max-width: min(920px, 92vw);
          max-height: 85vh;
          width: 100%;
          background: var(--card);
          border-radius: var(--radius);
          border: 1px solid var(--border);
          box-shadow: 0 16px 48px rgba(0,0,0,0.18);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .cdi-json-modal__head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.75rem;
          padding: 0.75rem 1rem;
          border-bottom: 1px solid var(--border);
        }
        .cdi-json-modal__title { font-size: 0.9375rem; margin: 0; font-weight: 600; }
        .cdi-json-modal__close {
          border: none;
          background: transparent;
          font-size: 1.25rem;
          line-height: 1;
          cursor: pointer;
          color: var(--muted-foreground);
          padding: 0.25rem 0.5rem;
          border-radius: calc(var(--radius) - 2px);
        }
        .cdi-json-modal__close:hover { background: var(--muted); color: var(--foreground); }
        .cdi-json-modal__pre {
          margin: 0;
          padding: 1rem;
          overflow: auto;
          flex: 1;
          font-family: var(--mono);
          font-size: 0.75rem;
          line-height: 1.45;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .page-foot {
          margin-top: 2.5rem;
          padding-top: 1.25rem;
          border-top: 1px solid var(--border);
          text-align: center;
          font-size: 0.75rem;
          color: var(--muted-foreground);
        }
        @media print {
          .sidebar { display: none; }
          .main { max-width: 100%; padding: 1rem; }
          .tab-panel { display: block !important; page-break-before: always; }
          .tab-panel:first-of-type { page-break-before: auto; }
          .evidence-card { break-inside: avoid; }
          .view-mode-bar { display: none; }
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
          .main { padding: 1.25rem; }
        }
        """
