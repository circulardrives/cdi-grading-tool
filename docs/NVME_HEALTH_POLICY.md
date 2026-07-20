# NVMe Health Grading Policy

Spec baselines:

- [NVM Express Base Specification 2.3](https://nvmexpress.org/wp-content/uploads/NVM-Express-Base-Specification-Revision-2.3-2025.08.01-Ratified.pdf) §5.2.12.1.3 (SMART / Health Information, Log 02h)
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
| `percentage_used` > 100 | Yes | Spec allows >100; 100 alone is not automatic failure |
| Failed NVMe self-test | Yes | |
| `critical_comp_time` (CCTT) > 0 | Yes | Lifetime minutes at/above CCTEMP |
| `current_temperature` ≥ CCTEMP | Yes | Manufacturer critical composite threshold |
| `current_temperature` ≥ WCTEMP (below CCTEMP) | No (warning) | Manufacturer warning band |
| `warning_temp_time` (WCTT) > 0 | No (warning) | Lifetime minutes in warning band |
| Fixed YAML 55/60 °C | **Not used for NVMe** when grading current temp | HDD-oriented fallback for ATA/SCSI only |

Instant over-temp without lifetime history still surfaces as Critical Warning bit 1 (TTC) when the controller asserts it.

## OCP C0h predictive-fail algorithm (v1)

Applied only when `ocp_smart_log` is present. Missing C0h → skip (consumer NVMe).

Grounded in OCP DSSD v2.7 field definitions (SMART-3…SMART-19). This is a **CDI remanufacturing synthesis**, not a single OCP “predictive fail” attribute (OCP does not define one SMART PF bit).

| Input | Critical (F) | Warning | Skip |
|-------|--------------|---------|------|
| Capacitor Health | Present, not `0xFFFF`, and `< capacitor_health_min` (default 100) | — | `0xFFFF` / missing (no PLP) |
| Uncorrectable read error count | `> 0` | — | missing |
| End-to-end detected − corrected | `> 0` uncorrected | — | missing |
| Bad user NAND normalized | `< bad_user_nand_critical` (default 50) | `< bad_user_nand_warning` (default 90) | missing / `0xFFFF` |
| System data % used | `≥ 100` | `≥ system_data_warn` (default 90) | missing |
| Incomplete shutdowns | — | `≥ incomplete_shutdowns_warn` (default 10) | — |
| Thermal throttling events / status | — | status ≥ 2 or events ≥ throttle_events_warn | — |
| Soft ECC error count | — | — | telemetry only (recoverable) |
| PCIe correctable errors | — | — | telemetry only |

Double-counting: base-log `media_errors` remains authoritative for NVMe MDIE. OCP uncorrectable reads add an independent media-path signal when C0h is present.

v2.7 is sufficient for algorithm v1. Newer OCP DSSD revisions can refine thresholds without changing the structure; track under GitHub #112.
