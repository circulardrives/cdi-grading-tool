#!/usr/bin/env python3
"""Build NVMe Fleet Dashboard HTML from JSON telemetry files."""

import json
import os
import glob

ICELAKE_DIR = "/Users/jm/Desktop/smart/icelake/"
GPU_DIR = "/Users/jm/Desktop/smart/gpu_server/"
OUTPUT = "/Users/jm/Desktop/smart/dashboard.html"

def get_ocp(ocp, key, default=0):
    v = ocp.get(key, default)
    if isinstance(v, dict):
        return v.get("lo", 0)
    return v if v is not None else default

def extract_drive(filepath, fleet):
    with open(filepath) as f:
        raw = json.load(f)

    sl = raw.get("smart_log", {})
    ic = raw.get("id_ctrl", {})
    ocp = raw.get("ocp_smart_log", {})

    data_units_written = sl.get("data_units_written", 0)
    data_units_read = sl.get("data_units_read", 0)
    bytes_per_unit = 512 * 1000
    tib = 1024**4
    written_tib = (data_units_written * bytes_per_unit) / tib if data_units_written else 0
    read_tib = (data_units_read * bytes_per_unit) / tib if data_units_read else 0

    phys_written_lo = get_ocp(ocp, "Physical media units written", 0)
    if isinstance(phys_written_lo, dict):
        phys_written_lo = phys_written_lo.get("lo", 0)
    phys_read_lo = get_ocp(ocp, "Physical media units read", 0)
    if isinstance(phys_read_lo, dict):
        phys_read_lo = phys_read_lo.get("lo", 0)

    raw_written_bytes = data_units_written * bytes_per_unit
    waf = (phys_written_lo / raw_written_bytes) if raw_written_bytes > 0 and phys_written_lo > 0 else 0

    poh = sl.get("power_on_hours", 0)
    tnvmcap = ic.get("tnvmcap", 0)
    cap_tb = tnvmcap / 1e12 if tnvmcap else 0
    cap_tib = tnvmcap / tib if tnvmcap else 0
    dwpd = 0
    if poh > 0 and cap_tib > 0:
        years = poh / 8760
        if years > 0:
            dwpd = written_tib / (cap_tib * years * 365)

    wr_ratio = (data_units_written / data_units_read) if data_units_read > 0 else 0

    max_erase = get_ocp(ocp, "Max User data erase counts", 0)
    min_erase = get_ocp(ocp, "Min User data erase counts", 0)
    erase_spread = max_erase - min_erase if max_erase >= min_erase else 0

    temp_k = sl.get("temperature", 0)
    temp_c = temp_k - 273 if temp_k > 0 else 0

    percent_used = sl.get("percent_used", 0)
    avail_spare = sl.get("avail_spare", 0)
    media_errors = sl.get("media_errors", 0)
    critical_warning = sl.get("critical_warning", 0)
    uncorr_read = get_ocp(ocp, "Uncorrectable read error count", 0)
    soft_ecc = get_ocp(ocp, "Soft ecc error count", 0)
    e2e_detected = get_ocp(ocp, "End to end detected errors", 0)
    e2e_corrected = get_ocp(ocp, "End to end corrected errors", 0)
    bad_user_raw = get_ocp(ocp, "Bad user nand blocks - Raw", 0)
    bad_user_norm = get_ocp(ocp, "Bad user nand blocks - Normalized", 0)
    bad_sys_raw = get_ocp(ocp, "Bad system nand blocks - Raw", 0)
    bad_sys_norm = get_ocp(ocp, "Bad system nand blocks - Normalized", 0)
    xor_recovery = get_ocp(ocp, "XOR recovery count", 0)
    thermal_events = get_ocp(ocp, "Number of Thermal throttling events", 0)
    throttle_status = get_ocp(ocp, "Current throttling status", 0)
    pcie_corr = get_ocp(ocp, "PCIe correctable error count", 0)
    incomplete_shut = get_ocp(ocp, "Incomplete shutdowns", 0)
    free_blocks = get_ocp(ocp, "Percent free blocks", 0)
    cap_health = get_ocp(ocp, "Capacitor health", 0)
    unaligned_io = get_ocp(ocp, "Unaligned I/O", 0)
    nuse = get_ocp(ocp, "NUSE - Namespace utilization", 0)
    plp_start = get_ocp(ocp, "PLP start count", 0)
    endurance_est = get_ocp(ocp, "Endurance estimate", 0)
    link_retrain = get_ocp(ocp, "PCIe Link Retraining Count", 0)
    ps_change = get_ocp(ocp, "Power State Change Count", 0)
    sys_data_pct = get_ocp(ocp, "System data percent used", 0)
    refresh_counts = get_ocp(ocp, "Refresh counts", 0)

    # Risk scoring — 8-category weighted model (aligned with generate_reports.py)
    scores = {}
    warning_temp_time = sl.get("warning_temp_time", 0)
    critical_comp_time = sl.get("critical_comp_time", 0)
    num_err_log_entries = sl.get("num_err_log_entries", 0)

    # 1. ECC Escalation Chain (0-40)
    ecc = 0
    if soft_ecc > 0:
        ecc += min(soft_ecc / 1_000_000, 1.0) * 10
    if xor_recovery > 0:
        ecc += min(xor_recovery / 100, 1.0) * 25
    if uncorr_read > 0:
        ecc += 40
    scores["ECC Escalation"] = min(ecc, 40)

    # 2. NAND Degradation Velocity (0-30)
    nand = 0
    if bad_user_raw > 0:
        nand += min(bad_user_raw / 10, 1.0) * 20
    if bad_sys_raw > 0:
        nand += 15
    if bad_user_norm < 100:
        nand += (100 - bad_user_norm) * 0.5
    scores["NAND Degradation"] = min(nand, 30)

    # 3. Wear Rate Projection (0-20)
    wear = 0
    if poh > 0 and percent_used > 0:
        rate_per_year = (percent_used / poh) * 8760
        yrs_rem = (100 - percent_used) / rate_per_year if rate_per_year > 0 else 999
        if yrs_rem < 1:
            wear = 20
        elif yrs_rem < 2:
            wear = 12
        elif yrs_rem < 3:
            wear = 6
    scores["Wear Rate"] = wear

    # 4. Thermal Stress (0-20)
    thermal = 0
    if warning_temp_time > 0:
        thermal += min(warning_temp_time / 3600, 1.0) * 5
    if thermal_events > 0:
        thermal += min(thermal_events / 10, 1.0) * 8
    if critical_comp_time > 0:
        thermal += 15
    if temp_c >= 70:
        thermal += 5
    scores["Thermal Stress"] = min(thermal, 20)

    # 5. Capacitor Aging (0-10)
    cap_score = 0
    if cap_health == 0:
        cap_score = 10
    elif cap_health < 80:
        cap_score = (80 - cap_health) * 0.2
    scores["Capacitor Aging"] = min(cap_score, 10)

    # 6. PCIe Link Instability (0-10)
    pcie_score = 0
    if pcie_corr > 100:
        pcie_score += min(pcie_corr / 10000, 1.0) * 5
    if link_retrain > 10:
        pcie_score += min(link_retrain / 100, 1.0) * 8
    scores["PCIe Instability"] = min(pcie_score, 10)

    # 7. GC Pressure Spiral (0-15)
    gc = 0
    if free_blocks < 5:
        gc += 5
    if waf > 5:
        gc += 5
    if free_blocks < 5 and waf > 5:
        gc += 5
    scores["GC Pressure"] = min(gc, 15)

    # 8. Infant Mortality (0-15)
    infant = 0
    if poh < 1000:
        if media_errors > 0 or uncorr_read > 0:
            infant = 15
        elif num_err_log_entries > 0:
            infant = 8
    scores["Infant Mortality"] = infant

    # Composite
    risk = min(sum(scores.values()), 100)
    risk = round(risk, 1)

    # Top factors (sorted desc, non-zero only, top 3)
    top_factors = sorted(scores.items(), key=lambda x: -x[1])
    factors = [(k, round(v, 1)) for k, v in top_factors if v > 0][:3]

    if risk >= 50: tier = "CRITICAL"
    elif risk >= 25: tier = "WARNING"
    elif risk >= 10: tier = "WATCH"
    else: tier = "HEALTHY"

    # Endurance projection
    years_remaining = None
    if poh > 0 and percent_used > 0:
        total_life_hours = poh / (percent_used / 100)
        remaining_hours = total_life_hours - poh
        years_remaining = round(remaining_hours / 8760, 2)

    return {
        "hostname": raw.get("hostname", ""),
        "device": raw.get("device", ""),
        "fleet": fleet,
        "sn": ic.get("sn", "").strip(),
        "mn": ic.get("mn", "").strip(),
        "fr": ic.get("fr", "").strip(),
        "cap_tb": round(cap_tb, 2),
        "temp_c": temp_c,
        "avail_spare": avail_spare,
        "spare_thresh": sl.get("spare_thresh", 0),
        "percent_used": percent_used,
        "poh": poh,
        "power_cycles": sl.get("power_cycles", 0),
        "unsafe_shutdowns": sl.get("unsafe_shutdowns", 0),
        "written_tib": round(written_tib, 2),
        "read_tib": round(read_tib, 2),
        "data_units_written": data_units_written,
        "data_units_read": data_units_read,
        "host_read_cmds": sl.get("host_read_commands", 0),
        "host_write_cmds": sl.get("host_write_commands", 0),
        "controller_busy_time": sl.get("controller_busy_time", 0),
        "critical_warning": critical_warning,
        "media_errors": media_errors,
        "num_err_log_entries": sl.get("num_err_log_entries", 0),
        "warning_temp_time": sl.get("warning_temp_time", 0),
        "critical_comp_time": sl.get("critical_comp_time", 0),
        "thm_temp1_trans": sl.get("thm_temp1_trans_count", 0),
        "thm_temp2_trans": sl.get("thm_temp2_trans_count", 0),
        "waf": round(waf, 2),
        "dwpd": round(dwpd, 4),
        "wr_ratio": round(wr_ratio, 3),
        "uncorr_read": uncorr_read,
        "soft_ecc": soft_ecc,
        "e2e_detected": e2e_detected,
        "e2e_corrected": e2e_corrected,
        "bad_user_raw": bad_user_raw,
        "bad_user_norm": bad_user_norm,
        "bad_sys_raw": bad_sys_raw,
        "bad_sys_norm": bad_sys_norm,
        "xor_recovery": xor_recovery,
        "thermal_events": thermal_events,
        "throttle_status": throttle_status,
        "pcie_corr": pcie_corr,
        "link_retrain": link_retrain,
        "incomplete_shut": incomplete_shut,
        "free_blocks": free_blocks,
        "cap_health": cap_health,
        "unaligned_io": unaligned_io,
        "nuse": nuse,
        "plp_start": plp_start,
        "endurance_est": endurance_est,
        "ps_change": ps_change,
        "sys_data_pct": sys_data_pct,
        "refresh_counts": refresh_counts,
        "erase_max": max_erase,
        "erase_min": min_erase,
        "erase_spread": erase_spread,
        "phys_written_lo": phys_written_lo,
        "phys_read_lo": phys_read_lo,
        "risk_score": risk,
        "risk_tier": tier,
        "risk_factors": factors,
        "years_remaining": years_remaining,
    }


def main():
    icelake_files = set(os.listdir(ICELAKE_DIR))
    gpu_files = set(os.listdir(GPU_DIR))

    drives = []
    errors = 0

    # icelake files -> storage fleet
    for fname in sorted(icelake_files):
        if not fname.endswith(".json"):
            continue
        try:
            d = extract_drive(os.path.join(ICELAKE_DIR, fname), "storage")
            drives.append(d)
        except Exception as e:
            errors += 1

    # gpu_server files NOT in icelake -> gpu fleet
    gpu_only = gpu_files - icelake_files
    for fname in sorted(gpu_only):
        if not fname.endswith(".json"):
            continue
        try:
            d = extract_drive(os.path.join(GPU_DIR, fname), "gpu")
            drives.append(d)
        except Exception as e:
            errors += 1

    print(f"Extracted {len(drives)} drives ({errors} errors/malformed)")

    # Build HTML
    data_json = json.dumps(drives, separators=(",", ":"))
    html = build_html(data_json)
    with open(OUTPUT, "w") as f:
        f.write(html)
    print(f"Wrote {OUTPUT} ({len(html)} bytes)")


def build_html(data_json):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FarmGPU NVMe Fleet Dashboard</title>
<style>
@import url("https://fonts.googleapis.com/css2?family=Spline+Sans:wght@300;400;500;600;700&family=Spline+Sans+Mono:wght@400;500;600&display=swap");
* {{ margin:0; padding:0; box-sizing:border-box; }}
:root {{
  --red: #c0392b;
  --sidebar-w: 220px;
  --bg: #F3FFE5; --card-bg: #F3FFE5; --border: #c8d9b0;
  --text: #000000; --text-muted: #444;
  --font-sans: "Spline Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "Spline Sans Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px;
}}
body {{ font-family: var(--font-sans); background: var(--bg); color: var(--text); display: flex; min-height: 100vh; }}
.sidebar {{ width: var(--sidebar-w); background: var(--bg); color: var(--text); position: fixed; top:0; left:0; bottom:0; display:flex; flex-direction:column; z-index:100; border-right: 1px solid var(--border); }}
.sidebar h2 {{ padding: 20px; font-size: 18px; color: var(--text); border-bottom: 1px solid var(--border); font-weight: 700; display:flex; align-items:center; gap:10px; }}
.sidebar nav a {{ display:flex; align-items:center; padding: 12px 20px; color: var(--text-muted); text-decoration:none; font-size:14px; border-left: 3px solid transparent; transition: all .15s; gap:10px; }}
.sidebar nav a:hover, .sidebar nav a.active {{ background: #e7ffcc; color: #000; border-left-color: #000; }}
.sidebar nav a svg {{ width:20px; height:20px; flex-shrink:0; }}
.main {{ margin-left: var(--sidebar-w); flex:1; padding: 24px; }}
.top-bar {{ display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin-bottom:20px; }}
.top-bar select, .top-bar input {{ padding: 8px 12px; border:1px solid var(--border); border-radius:var(--radius-sm); font-size:14px; background:var(--bg); color:var(--text); font-family:var(--font-sans); }}
.top-bar input {{ width: 260px; }}
.top-bar input::placeholder {{ color: var(--text-muted); }}
.tier-btns {{ display:flex; gap:6px; }}
.tier-btn {{ padding:6px 14px; border:1px solid var(--text); border-radius:20px; font-size:12px; font-weight:600; cursor:pointer; background:transparent; transition:all .15s; font-family:var(--font-sans); color:var(--text); }}
.tier-btn.active {{ background:#000; color:#F3FFE5; }}
.tier-btn[data-tier="CRITICAL"] {{ border-color:var(--red); color:var(--red); }}
.tier-btn[data-tier="CRITICAL"].active {{ background:var(--red); color:#fff; }}
.summary-cards {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr)); gap:12px; margin-bottom:20px; }}
.s-card {{ background:var(--bg); border-radius:var(--radius-md); padding:16px; border:1px solid var(--border); }}
.s-card .label {{ font-size:11px; text-transform:uppercase; color:var(--text-muted); letter-spacing:.5px; }}
.s-card .val {{ font-size:24px; font-weight:700; margin-top:4px; font-family:var(--font-mono); color:var(--text); }}
.section {{ display:none; }}
.section.active {{ display:block; }}
.table-wrap {{ overflow-x:auto; background:var(--bg); border-radius:var(--radius-md); border:1px solid var(--border); }}
table {{ width:100%; border-collapse:collapse; font-size:12px; font-family:var(--font-mono); color:var(--text); }}
thead th {{ position:sticky; top:0; background:var(--bg); padding:8px 6px; text-align:left; border-bottom:2px solid #000; cursor:pointer; white-space:nowrap; user-select:none; font-size:11px; z-index:10; color:var(--text); font-weight:700; }}
thead th:hover {{ background:#e7ffcc; }}
thead th .arrow {{ font-size:10px; margin-left:2px; }}
tbody td {{ padding:6px; border-bottom:1px solid var(--border); white-space:nowrap; color:var(--text); }}
tbody tr {{ transition: background .1s; }}
tbody tr:hover {{ background: #e7ffcc !important; }}
tr.row-CRITICAL {{ background: #fde8e6; }}
tr.row-WARNING {{ background: var(--bg); }}
tr.row-WATCH {{ background: var(--bg); }}
tr.row-HEALTHY {{ background: var(--bg); }}
.risk-cell {{ display:inline-block; padding:2px 8px; border-radius:4px; font-weight:700; font-size:11px; min-width:36px; text-align:center; }}
.risk-CRITICAL {{ background:var(--red); color:#fff; }}
.risk-WARNING {{ background:#000; color:#F3FFE5; }}
.risk-WATCH {{ background:var(--border); color:#000; }}
.risk-HEALTHY {{ background:transparent; color:var(--text); border:1px solid var(--border); }}
.detail-row td {{ padding:0 !important; }}
.detail-card {{ padding:16px 20px; background:var(--bg); border-top:1px solid var(--border); }}
.detail-card h3 {{ margin-bottom:12px; font-size:14px; color:var(--text); }}
.detail-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(220px,1fr)); gap:6px 20px; font-size:12px; }}
.detail-grid .dg-item {{ display:flex; justify-content:space-between; padding:2px 0; }}
.detail-grid .dg-item .dg-label {{ color:var(--text-muted); }}
.detail-grid .dg-item .dg-val {{ font-weight:600; color:var(--text); }}
.pred-card {{ background:var(--bg); border:1px solid var(--border); border-radius:var(--radius-lg); padding:16px; margin-bottom:12px; }}
.pred-card h4 {{ margin-bottom:8px; font-size:14px; display:flex; align-items:center; gap:8px; color:var(--text); }}
.risk-bar-outer {{ background:var(--border); border-radius:4px; height:12px; width:200px; display:inline-block; vertical-align:middle; margin-right:8px; }}
.risk-bar-inner {{ height:100%; border-radius:4px; transition:width .3s; }}
.factor-list {{ margin:8px 0; font-size:12px; list-style:none; }}
.factor-list li {{ margin:3px 0; display:flex; align-items:center; gap:8px; color:var(--text); }}
.factor-badge {{ display:inline-block; padding:1px 6px; border-radius:3px; font-weight:700; font-size:10px; min-width:28px; text-align:center; background:#000; color:#F3FFE5; }}
.ecc-chain {{ display:flex; align-items:center; gap:6px; margin:8px 0; font-size:12px; flex-wrap:wrap; color:var(--text); }}
.ecc-chain .ecc-node {{ padding:4px 10px; border-radius:4px; border:1px solid var(--border); background:var(--bg); color:var(--text-muted); }}
.ecc-chain .ecc-node.ecc-active {{ border-color:var(--red); background:#fde8e6; font-weight:700; color:var(--red); }}
.ecc-chain .ecc-arrow {{ color:var(--text-muted); }}
.action-box {{ margin-top:8px; padding:8px 12px; background:var(--bg); border:1px solid var(--border); border-radius:var(--radius-sm); font-size:12px; color:var(--text); display:flex; align-items:center; gap:8px; }}
.action-box svg {{ width:16px; height:16px; flex-shrink:0; }}
.endurance-bar {{ display:flex; align-items:center; gap:8px; margin-top:6px; font-size:12px; color:var(--text); }}
.host-link {{ color:#000; cursor:pointer; text-decoration:underline; font-weight:600; }}
.icon-inline {{ width:16px; height:16px; vertical-align:middle; display:inline-block; }}
.flag-red {{ color:var(--red); }}
@media(max-width:768px) {{
  .sidebar {{ width:60px; }} .sidebar h2 span.brand-text, .sidebar nav a span.nav-label {{ display:none; }}
  .main {{ margin-left:60px; padding:12px; }}
}}
</style>
</head>
<body>
<div class="sidebar">
  <h2><span class="brand-text">FarmGPU Fleet</span></h2>
  <nav>
    <a href="#" class="active" data-page="dashboard"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25a2.25 2.25 0 0 1-2.25-2.25v-2.25Z" /></svg><span class="nav-label">Dashboard</span></a>
    <a href="#" data-page="drives"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" /></svg><span class="nav-label">Drives</span></a>
    <a href="#" data-page="hosts"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M21.75 17.25v-.228a4.5 4.5 0 0 0-.12-1.03l-2.268-9.64a3.375 3.375 0 0 0-3.285-2.602H7.923a3.375 3.375 0 0 0-3.285 2.602l-2.268 9.64a4.5 4.5 0 0 0-.12 1.03v.228m19.5 0a3 3 0 0 1-3 3H5.25a3 3 0 0 1-3-3m19.5 0a3 3 0 0 0-3-3H5.25a3 3 0 0 0-3 3m16.5 0h.008v.008H18.75v-.008ZM15 17.25h.008v.008H15v-.008Z" /></svg><span class="nav-label">Hosts</span></a>
    <a href="#" data-page="predictive"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg><span class="nav-label">Predictive</span></a>
    <a href="#" data-page="about"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" /></svg><span class="nav-label">About</span></a>
  </nav>
</div>
<div class="main">
  <!-- TOP BAR -->
  <div class="top-bar">
    <select id="fleetSel"><option value="all">All Fleets</option><option value="storage">Storage</option><option value="gpu">GPU</option></select>
    <input id="searchBox" type="text" placeholder="Search hostname or serial...">
    <div class="tier-btns">
      <button class="tier-btn active" data-tier="ALL">ALL</button>
      <button class="tier-btn" data-tier="CRITICAL">CRITICAL</button>
      <button class="tier-btn" data-tier="WARNING">WARNING</button>
      <button class="tier-btn" data-tier="WATCH">WATCH</button>
      <button class="tier-btn" data-tier="HEALTHY">HEALTHY</button>
    </div>
  </div>

  <!-- DASHBOARD SECTION -->
  <div id="sec-dashboard" class="section active">
    <div class="summary-cards" id="summaryCards"></div>
    <div class="table-wrap"><table id="driveTable"><thead></thead><tbody></tbody></table></div>
  </div>

  <!-- DRIVES SECTION (same table, different nav highlight) -->
  <div id="sec-drives" class="section">
    <div class="summary-cards" id="summaryCards2"></div>
    <div class="table-wrap"><table id="driveTable2"><thead></thead><tbody></tbody></table></div>
  </div>

  <!-- HOSTS SECTION -->
  <div id="sec-hosts" class="section">
    <div class="table-wrap"><table id="hostTable"><thead></thead><tbody></tbody></table></div>
  </div>

  <!-- PREDICTIVE SECTION -->
  <div id="sec-predictive" class="section">
    <div id="predPanel"></div>
  </div>

  <!-- ABOUT SECTION -->
  <div id="sec-about" class="section">
    <div style="max-width:640px;padding:20px;">
      <h2>FarmGPU NVMe Fleet Dashboard</h2>
      <p style="margin:12px 0;">Interactive SMART telemetry explorer for NVMe drives across storage and GPU fleets. Provides risk scoring, predictive failure analysis, and fleet-level statistics.</p>
      <p style="margin:12px 0;">Data is embedded at build time from JSON telemetry files. Risk scores are computed from an 8-category weighted composite model: ECC Escalation (0-40), NAND Degradation (0-30), Wear Rate (0-20), Thermal Stress (0-20), GC Pressure (0-15), Infant Mortality (0-15), PCIe Instability (0-10), Capacitor Aging (0-10).</p>
      <p style="margin:12px 0;font-size:12px;color:var(--text-muted);">Self-contained HTML. No external dependencies beyond Google Fonts.</p>
    </div>
  </div>
</div>

<script>
// Heroicon SVG helpers (outline, 24px viewBox, inline as 16px)
const HI = {{
  excTriangle: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>`,
  excCircle: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" /></svg>`,
  fire: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="M15.362 5.214A8.252 8.252 0 0 1 12 21 8.25 8.25 0 0 1 6.038 7.047 8.287 8.287 0 0 0 9 9.601a8.983 8.983 0 0 1 3.361-6.867 8.21 8.21 0 0 0 3 2.48Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M12 18a3.75 3.75 0 0 0 .495-7.468 5.99 5.99 0 0 0-1.925 3.547 5.975 5.975 0 0 1-2.133-1.001A3.75 3.75 0 0 0 12 18Z" /></svg>`,
  checkCircle: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>`,
  wrench: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437 1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008Z" /></svg>`,
  bolt: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z" /></svg>`,
  shieldExc: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.25-8.25-3.286Zm0 13.036h.008v.008H12v-.008Z" /></svg>`,
  arrowRight: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>`,
  clock: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>`,
  eye: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="icon-inline"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>`,
}};
// Map factor category to icon
function factorIcon(name) {{
  if (name.includes("ECC")) return HI.bolt;
  if (name.includes("NAND")) return HI.shieldExc;
  if (name.includes("Wear")) return HI.clock;
  if (name.includes("Thermal")) return HI.fire;
  if (name.includes("Capacitor")) return HI.bolt;
  if (name.includes("PCIe")) return HI.excCircle;
  if (name.includes("GC")) return HI.excCircle;
  if (name.includes("Infant")) return HI.excTriangle;
  return HI.excCircle;
}}
// Action icon — red for errors, black otherwise
function actionIcon(score) {{
  if (score >= 25) return `<span class="flag-red">${{HI.excTriangle}}</span>`;
  if (score >= 10) return `${{HI.eye}}`;
  return `${{HI.checkCircle}}`;
}}

const DRIVE_DATA = {data_json};

// State
let currentFleet = "all";
let searchQuery = "";
let tierFilter = "ALL";
let sortCol = "risk_score";
let sortDir = -1; // -1 = desc
let hostSortCol = "worst_risk";
let hostSortDir = -1;
let expandedRow = null;
let hostFilterHostname = null;

// Columns definition
const COLS = [
  ["risk_score","Risk",60],["risk_tier","Tier",70],["fleet","Fleet",60],["hostname","Hostname",130],
  ["sn","Serial",170],["mn","Model",200],["fr","FW",80],["cap_tb","Cap TB",65],
  ["temp_c","Temp C",55],["avail_spare","Spare%",55],["percent_used","Used%",50],
  ["poh","POH",60],["power_cycles","PwrCyc",55],["unsafe_shutdowns","UnsafeSD",60],
  ["written_tib","Wr TiB",70],["read_tib","Rd TiB",70],["waf","WAF",50],["dwpd","DWPD",55],
  ["media_errors","MediaErr",60],["uncorr_read","UncorrRd",60],["soft_ecc","SoftECC",70],
  ["e2e_detected","E2E",45],["bad_user_raw","BadNAND",55],["pcie_corr","PCIeErr",55],
  ["link_retrain","LinkRet",50],["free_blocks","Free%",45],["cap_health","CapH%",45],
  ["thermal_events","ThrtEvt",50],["erase_max","ErMax",50],["erase_spread","ErSprd",50]
];

const HOST_COLS = [
  ["hostname","Hostname",150],["fleet","Fleet",70],["drive_count","#Drives",60],
  ["avg_temp","Avg Temp",70],["max_temp","Max Temp",70],["avg_poh","Avg POH",70],
  ["avg_written","Avg Wr TiB",80],["worst_risk","Worst Risk",75],
  ["critical_count","Critical",65],["warning_count","Warning",65]
];

function filtered() {{
  let d = DRIVE_DATA;
  if (currentFleet !== "all") d = d.filter(x => x.fleet === currentFleet);
  if (tierFilter !== "ALL") d = d.filter(x => x.risk_tier === tierFilter);
  if (searchQuery) {{
    const q = searchQuery.toLowerCase();
    d = d.filter(x => x.hostname.toLowerCase().includes(q) || x.sn.toLowerCase().includes(q));
  }}
  if (hostFilterHostname) d = d.filter(x => x.hostname === hostFilterHostname);
  d.sort((a,b) => {{
    let va = a[sortCol], vb = b[sortCol];
    if (typeof va === "string") return sortDir * va.localeCompare(vb);
    return sortDir * ((va||0) - (vb||0));
  }});
  return d;
}}

function renderSummary(containerId) {{
  const d = filtered();
  const n = d.length;
  const healthy = d.filter(x=>x.risk_tier==="HEALTHY").length;
  const crit = d.filter(x=>x.risk_tier==="CRITICAL").length;
  const warn = d.filter(x=>x.risk_tier==="WARNING").length;
  const avgTemp = n ? (d.reduce((s,x)=>s+x.temp_c,0)/n).toFixed(1) : 0;
  const avgSpare = n ? (d.reduce((s,x)=>s+x.avail_spare,0)/n).toFixed(1) : 0;
  const totalWr = d.reduce((s,x)=>s+x.written_tib,0).toFixed(1);
  const items = [
    [HI.eye, "Total Drives", n, ""],
    [HI.checkCircle, "Healthy", n ? (healthy/n*100).toFixed(1)+"%" : "0%", ""],
    [HI.excTriangle, "Critical", crit, crit > 0 ? "color:var(--red)" : ""],
    [HI.excCircle, "Warning", warn, ""],
    [HI.fire, "Avg Temp", avgTemp+"°C", ""],
    [HI.shieldExc, "Avg Spare", avgSpare+"%", ""],
    [HI.clock, "Total Written", totalWr+" TiB", ""]
  ];
  document.getElementById(containerId).innerHTML = items.map(([ic,l,v,s])=>
    `<div class="s-card"><div class="label">${{ic}} ${{l}}</div><div class="val" style="${{s}}">${{v}}</div></div>`
  ).join("");
}}

function buildTableHeader(table, cols, sCol, sDir, onSort) {{
  const thead = table.querySelector("thead");
  thead.innerHTML = "<tr>" + cols.map(([key,label])=>{{
    let arrow = "";
    if (key === sCol) arrow = sDir > 0 ? " &#9650;" : " &#9660;";
    return `<th data-col="${{key}}">${{label}}<span class="arrow">${{arrow}}</span></th>`;
  }}).join("") + "</tr>";
  thead.querySelectorAll("th").forEach(th => {{
    th.onclick = () => onSort(th.dataset.col);
  }});
}}

function fmtNum(v) {{
  if (v === null || v === undefined) return "-";
  if (typeof v === "number") {{
    if (Number.isInteger(v)) return v.toLocaleString();
    return v.toLocaleString(undefined, {{maximumFractionDigits:2}});
  }}
  return v;
}}

function renderDriveTable(tableId) {{
  const table = document.getElementById(tableId);
  buildTableHeader(table, COLS, sortCol, sortDir, col => {{
    if (sortCol === col) sortDir *= -1; else {{ sortCol = col; sortDir = col === "risk_score" ? -1 : 1; }}
    renderAll();
  }});
  const data = filtered();
  const tbody = table.querySelector("tbody");
  let html = "";
  data.forEach((d, i) => {{
    html += `<tr class="row-${{d.risk_tier}} drive-row" data-idx="${{i}}">`;
    COLS.forEach(([key]) => {{
      if (key === "risk_score") {{
        html += `<td><span class="risk-cell risk-${{d.risk_tier}}">${{d.risk_score}}</span></td>`;
      }} else if (key === "risk_tier") {{
        html += `<td><span class="risk-cell risk-${{d.risk_tier}}">${{d.risk_tier}}</span></td>`;
      }} else {{
        html += `<td>${{fmtNum(d[key])}}</td>`;
      }}
    }});
    html += `</tr>`;
    // detail row (hidden by default)
    html += `<tr class="detail-row" id="detail-${{i}}" style="display:none"><td colspan="${{COLS.length}}"><div class="detail-card">`;
    html += `<h3>${{d.sn}} — ${{d.mn}}</h3><div class="detail-grid">`;
    const allFields = [
      ["Hostname", d.hostname],["Device", d.device],["Fleet", d.fleet],
      ["Serial", d.sn],["Model", d.mn],["Firmware", d.fr],
      ["Capacity TB", d.cap_tb],["Temp (C)", d.temp_c],["Avail Spare %", d.avail_spare],
      ["Spare Threshold", d.spare_thresh],["Percent Used", d.percent_used],
      ["POH", fmtNum(d.poh)],["Power Cycles", fmtNum(d.power_cycles)],
      ["Unsafe Shutdowns", fmtNum(d.unsafe_shutdowns)],
      ["Written TiB", d.written_tib],["Read TiB", d.read_tib],
      ["Data Units Written", fmtNum(d.data_units_written)],["Data Units Read", fmtNum(d.data_units_read)],
      ["Host Read Cmds", fmtNum(d.host_read_cmds)],["Host Write Cmds", fmtNum(d.host_write_cmds)],
      ["Controller Busy Time", fmtNum(d.controller_busy_time)],
      ["Critical Warning", d.critical_warning],["Media Errors", fmtNum(d.media_errors)],
      ["Error Log Entries", fmtNum(d.num_err_log_entries)],
      ["Warning Temp Time", fmtNum(d.warning_temp_time)],["Critical Comp Time", d.critical_comp_time],
      ["Thm Temp1 Trans", d.thm_temp1_trans],["Thm Temp2 Trans", d.thm_temp2_trans],
      ["WAF", d.waf],["DWPD", d.dwpd],["Write/Read Ratio", d.wr_ratio],
      ["Uncorr Read Errors", fmtNum(d.uncorr_read)],["Soft ECC Errors", fmtNum(d.soft_ecc)],
      ["E2E Detected", fmtNum(d.e2e_detected)],["E2E Corrected", fmtNum(d.e2e_corrected)],
      ["Bad User NAND Raw", d.bad_user_raw],["Bad User NAND Norm", d.bad_user_norm],
      ["Bad System NAND Raw", d.bad_sys_raw],["Bad System NAND Norm", d.bad_sys_norm],
      ["XOR Recovery", fmtNum(d.xor_recovery)],
      ["Thermal Events", d.thermal_events],["Throttle Status", d.throttle_status],
      ["PCIe Corr Errors", fmtNum(d.pcie_corr)],["Link Retraining", d.link_retrain],
      ["Incomplete Shutdowns", fmtNum(d.incomplete_shut)],
      ["Free Blocks %", d.free_blocks],["Capacitor Health", d.cap_health],
      ["Unaligned I/O", fmtNum(d.unaligned_io)],["NUSE", fmtNum(d.nuse)],
      ["PLP Start Count", d.plp_start],["Endurance Estimate", fmtNum(d.endurance_est)],
      ["PS Change Count", d.ps_change],["Sys Data % Used", d.sys_data_pct],
      ["Refresh Counts", fmtNum(d.refresh_counts)],
      ["Erase Max", d.erase_max],["Erase Min", d.erase_min],["Erase Spread", d.erase_spread],
      ["Risk Score", d.risk_score],["Risk Tier", d.risk_tier],
      ["Est. Years Remaining", d.years_remaining !== null ? d.years_remaining : "N/A"],
    ];
    allFields.forEach(([l,v]) => {{
      html += `<div class="dg-item"><span class="dg-label">${{l}}</span><span class="dg-val">${{v}}</span></div>`;
    }});
    html += `</div></div></td></tr>`;
  }});
  tbody.innerHTML = html;
  // row click handler
  tbody.querySelectorAll(".drive-row").forEach(tr => {{
    tr.style.cursor = "pointer";
    tr.onclick = () => {{
      const idx = tr.dataset.idx;
      const det = document.getElementById("detail-"+idx);
      if (expandedRow && expandedRow !== det) expandedRow.style.display = "none";
      det.style.display = det.style.display === "none" ? "" : "none";
      expandedRow = det.style.display === "none" ? null : det;
    }};
  }});
}}

function buildHostData() {{
  const data = filtered();
  const map = {{}};
  data.forEach(d => {{
    if (!map[d.hostname]) map[d.hostname] = {{hostname:d.hostname, fleet:d.fleet, drives:[]}};
    map[d.hostname].drives.push(d);
  }});
  return Object.values(map).map(h => {{
    const ds = h.drives;
    const n = ds.length;
    return {{
      hostname: h.hostname,
      fleet: h.fleet,
      drive_count: n,
      avg_temp: +(ds.reduce((s,x)=>s+x.temp_c,0)/n).toFixed(1),
      max_temp: Math.max(...ds.map(x=>x.temp_c)),
      avg_poh: Math.round(ds.reduce((s,x)=>s+x.poh,0)/n),
      avg_written: +(ds.reduce((s,x)=>s+x.written_tib,0)/n).toFixed(2),
      worst_risk: Math.max(...ds.map(x=>x.risk_score)),
      critical_count: ds.filter(x=>x.risk_tier==="CRITICAL").length,
      warning_count: ds.filter(x=>x.risk_tier==="WARNING").length,
    }};
  }});
}}

function renderHostTable() {{
  const table = document.getElementById("hostTable");
  buildTableHeader(table, HOST_COLS, hostSortCol, hostSortDir, col => {{
    if (hostSortCol === col) hostSortDir *= -1; else {{ hostSortCol = col; hostSortDir = col === "worst_risk" ? -1 : 1; }}
    renderHostTable();
  }});
  let hosts = buildHostData();
  hosts.sort((a,b) => {{
    let va = a[hostSortCol], vb = b[hostSortCol];
    if (typeof va === "string") return hostSortDir * va.localeCompare(vb);
    return hostSortDir * ((va||0) - (vb||0));
  }});
  const tbody = table.querySelector("tbody");
  tbody.innerHTML = hosts.map(h => {{
    const rc = h.worst_risk >= 50 ? "CRITICAL" : h.worst_risk >= 25 ? "WARNING" : h.worst_risk >= 10 ? "WATCH" : "HEALTHY";
    return `<tr class="row-${{rc}}">` + HOST_COLS.map(([key]) => {{
      if (key === "hostname") return `<td><span class="host-link" data-host="${{h.hostname}}">${{h.hostname}}</span></td>`;
      if (key === "worst_risk") return `<td><span class="risk-cell risk-${{rc}}">${{h.worst_risk}}</span></td>`;
      return `<td>${{fmtNum(h[key])}}</td>`;
    }}).join("") + `</tr>`;
  }}).join("");
  tbody.querySelectorAll(".host-link").forEach(el => {{
    el.onclick = (e) => {{
      e.stopPropagation();
      hostFilterHostname = el.dataset.host;
      document.querySelector('[data-page="dashboard"]').click();
      document.getElementById("searchBox").value = el.dataset.host;
      searchQuery = el.dataset.host;
      renderAll();
    }};
  }});
}}

function renderPredictive() {{
  const data = DRIVE_DATA.filter(d => d.risk_score > 0).sort((a,b) => b.risk_score - a.risk_score);
  const panel = document.getElementById("predPanel");
  let html = "";
  data.forEach(d => {{
    const tierClass = d.risk_tier;
    const barColor = d.risk_score >= 25 ? "var(--red)" : "#000";
    html += `<div class="pred-card">`;
    html += `<h4><span class="risk-cell risk-${{tierClass}}">${{d.risk_score}}</span> ${{d.sn}} &mdash; ${{d.hostname}} (${{d.fleet}})</h4>`;
    html += `<div class="risk-bar-outer"><div class="risk-bar-inner" style="width:${{d.risk_score}}%;background:${{barColor}}"></div></div> <span style="font-size:12px">${{d.risk_score}}/100</span>`;
    // factors with icons
    if (d.risk_factors && d.risk_factors.length) {{
      html += `<ul class="factor-list">`;
      d.risk_factors.forEach(([name, score]) => {{
        const isErr = score >= 10;
        const badgeStyle = isErr ? "background:var(--red);color:#fff" : "background:#000;color:#F3FFE5";
        html += `<li><span ${{isErr?'class="flag-red"':''}}>${{factorIcon(name)}}</span><span class="factor-badge" style="${{badgeStyle}}">+${{score}}</span> ${{name}}</li>`;
      }});
      html += `</ul>`;
    }}
    // ECC chain
    const softActive = d.soft_ecc > 0;
    const xorActive = d.xor_recovery > 0;
    const uncorrActive = d.uncorr_read > 0;
    html += `<div class="ecc-chain">${{HI.bolt}} ECC Chain:
      <span class="ecc-node ${{softActive?'ecc-active':''}}">Soft ECC (${{fmtNum(d.soft_ecc)}})</span>
      <span class="ecc-arrow">${{HI.arrowRight}}</span>
      <span class="ecc-node ${{xorActive?'ecc-active':''}}">XOR Recovery (${{fmtNum(d.xor_recovery)}})</span>
      <span class="ecc-arrow">${{HI.arrowRight}}</span>
      <span class="ecc-node ${{uncorrActive?'ecc-active':''}}">Uncorrectable (${{fmtNum(d.uncorr_read)}})</span>
    </div>`;
    // Endurance
    if (d.years_remaining !== null) {{
      const pct = Math.min(d.percent_used, 100);
      html += `<div class="endurance-bar">Endurance: ${{pct}}% used, est. ${{d.years_remaining}} years remaining
        <div class="risk-bar-outer" style="width:120px"><div class="risk-bar-inner" style="width:${{pct}}%;background:${{pct>80?'var(--red)':'#000'}}"></div></div>
      </div>`;
    }}
    // Action (aligned with report model thresholds)
    let action = "No action needed.";
    if (d.risk_score >= 60) action = "Schedule replacement immediately. Back up data.";
    else if (d.risk_score >= 40) action = "Plan replacement within 30 days.";
    else if (d.risk_score >= 25) action = "Increase monitoring frequency.";
    else if (d.risk_score >= 10) action = "Monitor; review next cycle.";
    html += `<div class="action-box">${{actionIcon(d.risk_score)}}<strong>Recommended:</strong> ${{action}}</div>`;
    html += `</div>`;
  }});
  if (!html) html = `<div class="pred-card"><p style="color:var(--text-muted)">No drives with risk factors detected.</p></div>`;
  panel.innerHTML = html;
}}

function renderAll() {{
  expandedRow = null;
  renderSummary("summaryCards");
  renderSummary("summaryCards2");
  renderDriveTable("driveTable");
  renderDriveTable("driveTable2");
  renderHostTable();
  renderPredictive();
}}

// Event listeners
document.getElementById("fleetSel").onchange = e => {{ currentFleet = e.target.value; hostFilterHostname = null; renderAll(); }};
document.getElementById("searchBox").oninput = e => {{ searchQuery = e.target.value; if (!searchQuery) hostFilterHostname = null; renderAll(); }};
document.querySelectorAll(".tier-btn").forEach(btn => {{
  btn.onclick = () => {{
    document.querySelectorAll(".tier-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    tierFilter = btn.dataset.tier;
    renderAll();
  }};
}});
document.querySelectorAll(".sidebar nav a").forEach(a => {{
  a.onclick = e => {{
    e.preventDefault();
    document.querySelectorAll(".sidebar nav a").forEach(x => x.classList.remove("active"));
    a.classList.add("active");
    document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
    document.getElementById("sec-" + a.dataset.page).classList.add("active");
  }};
}});

// Initial render
renderAll();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
