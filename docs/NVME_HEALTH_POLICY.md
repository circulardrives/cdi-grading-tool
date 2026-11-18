# NVMe Health Grading Policy

Spec baselines:

- NVM Express Base Specification 2.4 (ratified 2026-07-31; [nvmexpress.org/specifications](https://nvmexpress.org/specifications/)): §5.2.13.1.3 / Figure 213 (SMART / Health Information, Log 02h), §5.2.13.1.7 / Figures 218–219 (Device Self-test, Log 06h), Figure 338 (Identify Controller WCTEMP / CCTEMP). In revision 2.3 the same content is §5.2.12.1.3 / Figure 210.
- [OCP Datacenter NVMe SSD Specification v2.7](Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md) (SMART C0h extended log)

Configurable knobs live in `src/cdi_health/config/thresholds.yaml` under `nvme` / `temperature` / `nvme.ocp`.

## Base log (02h) — always applied

| Signal | Grade F? | Notes |
|--------|----------|-------|
| SMART overall fail | Yes | `smart_status.passed == false` |
| Critical Warning any bit | Yes | Bits labeled in deductions (ASCBT, TTC, NDR, AMRO, …) |
| EGCWS any bit | Yes | When reported |
| `media_errors` (MDIE) > 0 | Yes | Unrecovered media/data integrity |
| `available_spare` < drive AVSPT | Yes | Prefer drive threshold; fallback default **10%** (not 97) |
| `available_spare` ≥ AVSPT | No (graded) | `abcdf`: A ≥ 80, B ≥ 60, C ≥ 40, else D (`available_spare_bands`); primary SSD health signal |
| `percentage_used` 80–99 | No | −5 at 80%, −10 at 90%; score only, never the letter |
| `percentage_used` ≥ 100 | `binary` only (> 100) | `abcdf`: graded **C**, **D** if any other warning; flag `ENDURANCE_EXCEEDED` (`endurance_exceeded_grade`, set F to restore the fail-gate) |
| Failed NVMe self-test (06h result 5–7) | Profile | `binary`: any failure is F. `abcdf`: 1 old → C, 1 recent / 2+ old → D, 2+ recent → F. Results 1–4, 8, 9 are aborts, not failures |
| `critical_comp_time` (CCTT) > 0 | Yes | Lifetime minutes at/above CCTEMP |
| `current_temperature` ≥ CCTEMP | Yes | Manufacturer critical composite threshold |
| `current_temperature` ≥ WCTEMP (below CCTEMP) | No (warning) | Manufacturer warning band |
| `warning_temp_time` (WCTT) > 0 | No (warning) | Lifetime minutes in warning band |
| Fixed YAML 55/60 °C | **Not used for NVMe** when grading current temp | HDD-oriented fallback for ATA/SCSI only |

Critical Warning bit 1 is set while a temperature is at or above its over-temperature threshold, or at or below its under-temperature threshold. The default over-temperature threshold for the composite temperature is **WCTEMP**, not CCTEMP, and the host can change it (Temperature Threshold feature). The bit is current state only and does not mean CCTEMP was reached.

**Open policy question.** Because any Critical Warning bit is a fail-gate, a drive scanned at or above WCTEMP normally grades F through bit 1 (and through smartctl's overall status, which for NVMe is simply "Critical Warning is zero"), so the "≥ WCTEMP → warning" row above is rarely reached. OCP 2.7 exempts bit 0 and bit 1 from its own self-test SMART check (SELFTST-1). A drive that reports no CCTEMP also holds CCTT at 0, and one that reports no WCTEMP or CCTEMP holds WCTT at 0.

## OCP C0h predictive-fail algorithm (v1)

Applied only when `ocp_smart_log` is present. Missing C0h → skip (consumer NVMe).

Grounded in OCP DSSD v2.7 field definitions (SMART-3…SMART-19). This is a **CDI remanufacturing synthesis**, not a single OCP “predictive fail” attribute (OCP does not define one SMART PF bit).

| Input | Critical (F) | Warning | Skip |
|-------|--------------|---------|------|
| Capacitor Health | Present, not `0xFFFF`, and `< capacitor_health_min` (default 100) | — | `0xFFFF` / missing (no PLP) |
| Uncorrectable read error count | `> 0` | — | missing |
| End-to-end detected − corrected | `> 0` uncorrected | — | missing |
| Bad user NAND normalized | `< bad_user_nand_critical` (default 50) | `< bad_user_nand_warning` (default 90) | missing / `0xFFFF` |
| System data % used | `≥ 100` | `≥ system_data_used_warning` (default 90) | missing |
| Incomplete shutdowns | — | `≥ incomplete_shutdowns_warning` (default 10) | — |
| Thermal throttling events / status | — | status ≥ 2 or events ≥ `thermal_throttle_events_warning` (default 20) | — |
| Soft ECC error count | — | — | telemetry only (recoverable) |
| PCIe correctable errors | — | — | telemetry only |

Double-counting: base-log `media_errors` remains authoritative for NVMe MDIE. OCP uncorrectable reads add an independent media-path signal when C0h is present.

v2.7 is sufficient for algorithm v1. Newer OCP DSSD revisions can refine thresholds without changing the structure; track under GitHub #112.
