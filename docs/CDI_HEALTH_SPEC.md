# CDI Health Specification

## Overview

The Circular Drive Initiative (CDI) Health Scanner provides a standardized method for assessing storage device health across **ATA/SATA**, **NVMe**, and **SCSI/SAS**. This document describes scoring, thresholds, data collection, **offline HTML reporting**, and how **NVMe log page 02h** (baseline health) relates to **OCP log page C0h** (extended datacenter telemetry).

**Fleet grouping:** Devices are classified for reporting and analysis by **transport** and **media** (for example SATA HDD, SAS HDD, SATA SSD, SAS SSD, NVMe SSD), using `transport_protocol`, `media_type` (HDD vs SSD), and `interface_link` where applicable.

**How to read this spec:** Start with the shared scoring rules, then use the drive-class section that matches the device:

- [SATA HDD](#sata-hdd)
- [SAS HDD](#sas-hdd)
- [SATA SSD](#sata-ssd)
- [SAS SSD](#sas-ssd)
- [NVMe SSD](#nvme-ssd)

## Health Scoring System

### Score Calculation

Health scores range from **0–100** (starting at 100). The calculator applies deductions for failed checks. Typical inputs include:

- **SMART Status**: Pass/Fail (critical)
- **Reallocated Sectors** (SATA): Count of reallocated sectors (**HDD sector curve** below)
- **Pending Sectors** (SATA): Count of sectors pending reallocation (**HDD sector curve** below)
- **Grown Defects** (SAS/SCSI): Same **numeric policy** as SATA HDD reallocated/pending (**HDD sector curve** below)
- **Uncorrectable Errors**: Uncorrectable read/write (ATA) and combined uncorrected errors (SCSI)
- **Temperature**: Operating temperature vs. maximum rated temperature
- **Percentage Used**: Wear level (SATA SSDs and NVMe SSDs; SAS SSDs when normalized endurance data is available)
- **Critical Warning / Media Errors**: NVMe (log **02h**)

### HDD sector defect curve (SATA and SAS)

For **rotating media (HDDs)**, **SATA** uses **reallocated** and **pending** counts; **SAS/SCSI** uses **grown defect** count (and the same failure scale). Each metric is scored **independently** (reallocated, pending, and grown defects can each contribute deductions).

Let:

- **C** = concern threshold (`grading.hdd_sector_concern_threshold`, default **2**): counts **≤ C** incur **no** deduction for that metric.
- **F** = failure threshold: **10** for `ata.maximum_reallocated_sectors`, `ata.maximum_pending_sectors`, and `scsi.maximum_grown_defects` (defaults).
- **M** = max deduction points for that metric (`grading.hdd_sector_defect_max_deduction_points`, default **10**).
- **E** = extra points per sector beyond **F** (`grading.hdd_sector_excess_points_per_sector`, default **1**), capped by **E_cap** (`grading.hdd_sector_excess_cap`, default **40**), so each metric’s deduction is clamped to **50** total (same ceiling style as uncorrectable-sector handling).

**Behavior** (matches the reference implementation):

| Count range | Severity | Points deducted |
|-------------|----------|-----------------|
| **≤ C** | — | **0** |
| **C < count < F** | Warning | **round((count − C) / (F − C) × M)**, then clamp to **\[1, M − 1\]** (so **1–9** with defaults) |
| **≥ F** | Critical | **min(50, M + min(E_cap, (count − F) × E))** |

**Example (defaults C=2, F=10, M=10, E=1, E_cap=40):** count **5** → raw **(5−2)/(10−2)×10 ≈ 3.75** → **4** points; count **10** → **10** points (no excess yet), critical; count **48** → **10 + min(40, 38) = 48** points, critical. Any critical result from this curve is a hard fail-gate and produces **F / score 0**.

The curve above is the **`binary`** profile's HDD policy. The default **`abcdf`** profile grades the same counters with graduated bands instead (see [Grading Pipeline (abcdf)](#grading-pipeline-abcdf-default)).

Other deductions in the same 0–100 model include **self-test** history, **temperature** warning/critical bands, **SSD wear** tiers, and **per-error** uncorrectable handling — see `src/cdi_health/classes/scoring.py` and `src/cdi_health/config/thresholds.yaml` for the full ruleset. Critical severity is a disposition-level fail-gate: it sets score **0** and grade **F** regardless of other telemetry. Warning/info deductions remain numeric and can produce A-D grades.

### Grade Assignment

- **A (90-100)**: Excellent - Drive is healthy and suitable for reuse
- **B (75-89)**: Good - Minor issues detected
- **C (60-74)**: Fair - Some degradation present
- **D (40-59)**: Poor - Significant issues detected
- **F (0-39)**: Failed - Drive should not be reused

Hard fail-gates override numeric deductions and always produce **F / score 0** (both profiles unless noted):

- SMART explicitly reports failure (`false`, `failed`, `bad`, etc.)
- The scan/disposition path marks the device operational state as **Fail**
- A **SCSI/SAS** drive answers TEST UNIT READY with a genuine *Not Ready* after one START UNIT retry (F-NO-RESPONSE; see [Readiness](#readiness-test-unit-ready))
- Self-test failures: any failed self-test (`binary`); two or more recent failures (`abcdf`, see [Self-test history](#self-test-history))
- NVMe critical warning or Endurance Group Critical Warning Summary is non-zero
- NVMe media/data-integrity error count is non-zero
- NVMe available spare is below the drive-reported threshold (AVSPT), or below the CDI fallback when no drive threshold is reported
- SSD percentage used **exceeds** `maximum_percentage_used` — **`binary` profile only**. Under `abcdf` a drive at/past rated endurance is graded **C** (or **D**), not failed; see [SSD endurance and available spare](#ssd-endurance-and-available-spare)
- HDD/SAS defect counts beyond the failure threshold (`binary`) or beyond the D band maximum (`abcdf`), uncorrectable errors beyond limit, or temperature above operating maximum

Unknown or unavailable SMART data alone is not a hard fail unless paired with failed operational state evidence. For example, an unresponsive/DOA device reported as **State=Fail** with unknown SMART is **F**, while a device with missing SMART data but no failed-state evidence is left to other telemetry and policy. **Missing data is never graded as healthy**, though: see [Missing and unknown data](#missing-and-unknown-data).

**Power-on hours (POH):** POH is collected and reported for ATA, NVMe, and SCSI/SAS devices. When a drive does not report POH (or cannot be read because it is not ready), POH is recorded as **Not Reported** — never as `0` — and carries the `POH_NOT_REPORTED` warning flag. Unknown POH does not apply the age cap and does not trigger the SMART-reset (POH = 0) heuristic.

CDI Health supports two selectable **grading profiles** (issues [#115](https://github.com/circulardrives/cdi-grading-tool/issues/115), [#125](https://github.com/circulardrives/cdi-grading-tool/issues/125)):

| Profile | How to select | POH role |
| --- | --- | --- |
| **`binary`** (aliases: `passfail`, `cdi`) | `grading.profile: binary` in thresholds.yaml, or `--grading-profile binary` | Telemetry only — not a grade threshold (this section’s historic CDI policy). |
| **`abcdf`** (aliases: `revert`, `graduated`) — **default** | `grading.profile: abcdf`, or `--grading-profile abcdf` | Revert Drive Grading Standard §5 **age cap**: POH caps the maximum achievable grade by drive class (enterprise/consumer). Disable age cap within abcdf via `grading.age_cap.enabled: false` while keeping graduated defect bands. |

Under **`binary`**, CDI grading uses explicit failure/defect indicators and numeric deductions; critical fail-gates (including any failed self-test) force Grade F. Certification is Yes/No.

Under **`abcdf`**, the full Revert Standard v2.0 pipeline applies (fail-gates → age cap → graduated bands → recency-weighted self-test → worst-attribute-wins → multi-factor → tri-state certification), with the CDI policy decisions documented in the next section. POH age cap is abcdf-only.

## Grading Pipeline (abcdf, default)

The `abcdf` profile computes a letter grade first and then a score consistent with that grade's band (`grading.grade_band_base_scores`: A 100, B 85, C 70, D 50, F 0, minus minor non-graded warnings, clamped to the band floor from `grading.grade_bands`).

1. **Stage 1 — fail-gates.** Any critical deduction (list above) → **F / 0**.
2. **Stage 2 — age cap (§5).** POH caps the best achievable grade by drive class (`grading.age_cap`):
   - Enterprise (SAS/SCSI, NVMe): > 40,000 h → max **B**; > 60,000 h → max **C**.
   - Consumer (ATA/SATA): > 20,000 h → max **B**; > 60,000 h → max **D**.
   - Unknown POH → no cap (flag `POH_NOT_REPORTED`).
3. **Stage 3 — per-attribute grades** (each recorded in `attribute_grades`):

   | Attribute | A | B | C | D | F |
   |---|---|---|---|---|---|
   | ATA reallocated / pending sectors | 0 | 1–9 | 10–50 | 51–100 | > 100 |
   | ATA uncorrectable errors | 0 | 1–5 | 6–25 | 26–100 | > 100 |
   | SCSI grown defects | 0 | 1–9 | 10–50 | 51–100 | > 100 |
   | SCSI uncorrected errors | 0 | 1–5 | 6–25 | 26–100 | > 100 |
   | SSD available spare (%) | ≥ 80 | ≥ 60 | ≥ 40 | < 40 and ≥ AVSPT | < AVSPT |
   | SSD endurance (percentage used ≥ 100%) | — | — | **C** | D with other warnings | — |
   | Self-test history | none | — | 1 old | 1 recent or 2+ old | 2+ recent |
   | Missing critical defect data | — | **B** (cap) | — | — | — |

4. **Worst-attribute-wins (§12.4).** The defect grade is the worst attribute grade.
5. **Multi-factor degradation (§12.5).** When 3+ attributes are independently C-or-worse, the defect grade drops one more level.
6. **Final grade (§12.6)** = the worse of the defect grade and the age cap.
7. **Certification (§12.7)** — tri-state: **A/B/C → certified**, **D → Advisory**, **F → not certified**. UNGRADED drives are not certified.

### SSD endurance and available spare

Applies to NVMe (`percentage_used`, `available_spare` / AVSPT from log 02h), SATA SSD, and SAS SSD endurance indicators (issue #133).

- **Percentage used is not a primary health signal below 100%.** Under 80% it has no effect. At/above **80%** a −5 point deduction applies, at/above **90%** −10 (`nvme.wear_warning_moderate/high`, `wear_moderate/high_deduction`). These are non-graded: they lower the score within the letter band but never change the letter.
- **At/past rated endurance (percentage used ≥ `maximum_percentage_used`, default 100%)** the drive is graded **C** (`nvme.endurance_exceeded_grade`), with warning flag `ENDURANCE_EXCEEDED`. If the drive has **any other warning** (another attribute below A, or another warning/critical deduction) the endurance attribute becomes **D**. A worse attribute still wins (e.g. spare below AVSPT → F). Setting `endurance_exceeded_grade: F` restores the historical F-ENDURANCE fail-gate. The `binary` profile keeps `> maximum_percentage_used` as a fail-gate.
- **Available spare is the primary SSD health signal** and is graded with `nvme.available_spare_bands` (minimum spare % per grade: A 80, B 60, C 40); below 40% but at/above the drive's AVSPT is D; below AVSPT is the F fail-gate. SATA SSD attribute **232** (*Available_Reservd_Space*) is graded with the same bands when smartctl names it as reserved space; at/below its own non-zero threshold is F. Under `binary`, spare in the D range is a −10 warning (`nvme.available_spare_low_deduction`).

### Readiness (TEST UNIT READY)

CDI issues SCSI TEST UNIT READY (`sg_turs`) to every device (issue #128):

- Only a genuine *Not Ready* sense (sg_turs exit 2) or medium/hardware error (exit 3) counts as **Not Ready**. A Not Ready drive is retried once after a best-effort START UNIT (`sg_start --start`).
- Tool missing, timeout, permission/open failure, or transport timeout → readiness **Unknown**, flag `TUR_UNAVAILABLE`. Not a fail-gate.
- **SCSI/SAS** Not Ready after retry → **F-NO-RESPONSE** fail-gate.
- **ATA/NVMe** Not Ready is waived when the drive returned readable SMART/health data (flag `TUR_NOT_READY`); the SAT/NVMe translation of TUR is not trusted over valid health data.

### Missing and unknown data

Missing counters are never read as zero/healthy (issue #134):

- Critical counters: ATA attribute **5**, ATA **197** (HDDs only), SCSI **grown defects** and **uncorrected errors**, NVMe **available spare**. When any is not reported, the drive carries `MISSING_DEFECT_DATA` and its grade is capped at **B** (`grading.missing_defect_data_grade_cap`; an attribute grade under `abcdf`, a grade cap under `binary`).
- ATA 198, and ATA 197 on SSDs, are not treated as critical because many healthy drives omit them.
- SCSI grown-defect sentinel `-1` means *not reported*.

### Self-test history

- **NVMe** results are decoded per NVM Express Log Page 06h: result nibble **0** = passed; **5, 6, 7** = failed (fatal error, unknown segment failed, segment failed); **1–4, 8, 9** = aborted; **Fh** = unused entry. Aborted tests are not failures (issue #130).
- **ATA/SCSI** use smartctl's explicit pass/fail status; aborted/in-progress entries are ignored.
- `abcdf` recency weighting (§10): a failure is *recent* when it occurred within `grading.selftest_recent_poh_window` (default 1,000) power-on hours of the current POH; entries without POH are treated as recent. One old failure → C; one recent or 2+ old → D; 2+ recent → F.
- `binary`: any failed self-test is a fail-gate.

### Warning flags and UNGRADED

Every result carries `grading_status` (`GRADED` / `UNGRADED`), `warning_flags`, and `fail_reason_codes` (§13/§15).

- **UNGRADED** (no letter grade, not counted as failed, not certified): security-locked drive, SMART unreadable, device open failure/timeout, USB or RAID passthrough failure, unsupported protocol (`ungraded_reasons`).
- **Warning flags:** `SMART_RESET_SUSPECTED`, `DUPLICATE_SERIAL`, `TUR_UNAVAILABLE`, `TUR_NOT_READY`, `POH_NOT_REPORTED`, `MISSING_DEFECT_DATA`, `ENDURANCE_EXCEEDED`.

### Thresholds configuration

`src/cdi_health/config/thresholds.yaml` is loaded by default. An explicitly supplied config (`--config`, API `config`) that is missing, unparseable, has unknown keys, wrong value types, or non-monotonic grade bands is a **hard error** (CLI exit code 2, API HTTP 400) — CDI never silently grades with a different policy (issue #137). An empty file means "use defaults".

## Drive-Class Health Rules

Use these sections as the primary grading reference. The report uses the same five classes: **SATA HDD**, **SAS HDD**, **SATA SSD**, **SAS SSD**, and **NVMe SSD**.

### Shared Rules

These rules apply to every drive class:

- **SMART status must pass.** Explicit failure (`false`, `failed`, `bad`, etc.) is a hard fail-gate.
- **Operational State must not be Fail.** A failed scan/disposition state is a hard fail-gate even when SMART is unavailable or unknown.
- **Temperature must remain within operating range.** Exceeding the maximum operating temperature is a hard fail-gate; warning temperature is a warning deduction.
- **Power-on hours depend on grading profile.** In the **`binary`** profile, POH is telemetry only. In the **`abcdf`** (Revert) profile, POH applies the §5 age cap (see POH section above; issues #115 / #125).
- **Unknown SMART alone is not failure.** Missing or unavailable SMART data does not hard-fail a device unless paired with failed-state evidence or another critical health signal.
- **SMART warning is not always SMART failure.** A warning means some vendor threshold or advisory condition needs inspection; CDI hard-fails only explicit SMART failure or another critical health signal.

### SATA HDD

SATA HDDs use ATA SMART plus ATA Device Statistics. CDI treats sector defects and uncorrectable media errors as the primary health signals; mechanical age and usage counters are context.

**Collected health data:**

- ATA SMART status.
- SMART Attribute **5**: Reallocated Sectors Count.
- SMART Attribute **197**: Current Pending Sector Count.
- SMART Attribute **198**: Offline Uncorrectable Sector Count.
- SMART Attribute **188**: Command Timeout, for trend/diagnostic review.
- SMART Attribute **199**: UDMA CRC Error Count, usually cable/controller/transport related.
- Device Statistics Log, especially rotating-media statistics, temperature statistics, power cycles, load cycles, and POH.

**Affects score:**

- Reallocated sectors use the **HDD sector defect curve**.
- Pending sectors use the **HDD sector defect curve**.
- Offline uncorrectable sectors use per-error uncorrectable handling.
- Temperature warning/critical bands apply.

**Hard-fails:**

- SMART failure.
- Operational State=Fail.
- Reallocated sectors or pending sectors at/above the configured failure threshold.
- Offline uncorrectable sectors above the configured uncorrectable-error limit.
- Temperature above maximum operating temperature.

**Telemetry only:**

- POH, power cycles, load cycles, start/stop count, spin-up/seek statistics, command timeouts, CRC errors, and other mechanical/transport context unless a future spec revision defines explicit thresholds. CRC growth should prompt cable/controller investigation, not automatic drive failure.

### SAS HDD

SAS HDDs use SCSI/SAS SMART data, SCSI grown-defect information, and SCSI error counters. CDI maps grown defects to the same HDD defect policy used for SATA HDD sector defects.

**Collected health data:**

- SCSI/SAS SMART status.
- Grown defect count.
- SCSI Error Counter Log: total uncorrected read, write, and verify errors.
- Corrected read/write error counters, for trend review.
- Non-medium error count.
- Temperature and POH where reported.

**Affects score:**

- Grown defects use the **HDD sector defect curve**.
- Combined uncorrected read/write/verify errors use per-error uncorrectable handling.
- Temperature warning/critical bands apply.

**Hard-fails:**

- SMART failure.
- Operational State=Fail.
- Grown defects at/above the configured failure threshold.
- Combined uncorrected read/write/verify errors above the configured SCSI uncorrected-error limit.
- Temperature above maximum operating temperature.

**Telemetry only:**

- Non-medium errors, corrected-error trends, POH, and other transport/controller/path counters are collected and reported for trend review, but are not currently direct grade thresholds.

### SATA SSD

SATA SSDs use ATA SMART, vendor-specific wear indicators, and ATA Device Statistics where available. CDI does not use the HDD sector defect curve for SATA SSD wear.

**Collected health data:**

- ATA SMART status.
- SMART Attribute **198**: Offline Uncorrectable Sector Count.
- SMART Attribute **199**: UDMA CRC Error Count, usually cable/controller/transport related.
- Vendor-specific wear indicators, including attributes such as **231**, **177**, **169**, **202**, and **232** when present.
- Solid State Device Statistics percentage-used endurance when available.
- Temperature and POH.

**Affects score:**

- SSD percentage used / endurance per [SSD endurance and available spare](#ssd-endurance-and-available-spare). Wear attributes are interpreted from the smartctl attribute **name** first, then per-vendor rules (e.g. Micron/Crucial **202** *Percent_Lifetime_Remain* and Kingston/SandForce **231** *SSD_Life_Left* report life **remaining**); an unnamed generic 202/230/231 with unknown semantics is not used as a wear value.
- Attribute **232** available reserved space, when named, is graded like NVMe available spare.
- Reallocated or pending defect counts, when present, use SSD-style per-sector handling rather than the HDD sector defect curve.
- Offline uncorrectable sectors use per-error uncorrectable handling.
- Temperature warning/critical bands apply.

**Hard-fails:**

- SMART failure.
- Operational State=Fail.
- SSD percentage used exceeds the CDI threshold (`binary` only; `abcdf` grades C/D).
- Available reserved space (232) at/below its threshold.
- Uncorrectable errors above the configured limit.
- Temperature above maximum operating temperature.

**Telemetry only:**

- POH, power cycles, CRC errors, vendor-specific raw SMART values that cannot be normalized, and general device statistics not mapped to explicit health policy.

### SAS SSD

SAS SSDs use SCSI/SAS SMART data, SCSI error counters, and any SSD endurance fields reported by the device. CDI treats media/error signals as health inputs and keeps non-medium errors as telemetry until an explicit threshold is defined.

**Collected health data:**

- SCSI/SAS SMART status.
- SCSI Error Counter Log: total uncorrected read, write, and verify errors.
- Corrected read/write error counters, for trend review.
- SSD endurance / percentage-used data when available.
- Non-medium error count.
- Temperature and POH.

**Affects score:**

- SSD percentage used / endurance (`scsi_percentage_used_endurance_indicator`) per [SSD endurance and available spare](#ssd-endurance-and-available-spare).
- Combined uncorrected read/write/verify errors use per-error uncorrectable handling.
- Grown defects, if reported for an SSD, use SSD-style per-defect handling rather than the HDD defect curve.
- Temperature warning/critical bands apply.

**Hard-fails:**

- SMART failure.
- Operational State=Fail.
- SSD percentage used exceeds the CDI threshold when normalized data is available (`binary` only; `abcdf` grades C/D).
- Combined uncorrected read/write/verify errors above the configured SCSI uncorrected-error limit.
- Temperature above maximum operating temperature.

**Telemetry only:**

- Non-medium errors, corrected-error trends, POH, and controller/transport counters unless a future spec revision defines direct thresholds.

### NVMe SSD

NVMe SSDs use the standard **SMART / Health Information** log page (**log identifier 02h**) for grading. Optional **OCP** log page **C0h** adds datacenter telemetry but is not required for grading.

**Collected health data from log 02h:**

- Critical warning bitfield.
- Percentage used.
- Available spare and available spare threshold.
- Media and data-integrity errors.
- Temperature.
- Data units read/written, host reads/writes, power cycles, unsafe shutdowns, error log entries, and POH.
- NVMe self-test log when present.

**Affects score:**

- Percentage used / endurance — points only below 100%; C/D at/past rated endurance ([details](#ssd-endurance-and-available-spare)).
- Available spare — graded A–D by `nvme.available_spare_bands`, compared to the drive-reported threshold; CDI uses its configured fallback only when the drive does not report a threshold.
- Temperature warning/critical bands.
- NVMe self-test result.

**Hard-fails:**

- SMART failure.
- Operational State=Fail.
- Critical warning is non-zero.
- Media/data-integrity error count is non-zero.
- Available spare is below threshold (AVSPT).
- Percentage used exceeds the CDI threshold (`binary` only; `abcdf` grades C/D).
- Failed NVMe self-tests (result codes 5–7) per [Self-test history](#self-test-history). CDI accepts both `entries[].result` and smartctl `table[].self_test_result.value` shapes.
- Temperature above maximum operating temperature.

**Telemetry only:**

- POH, data units read/written, host reads/writes, controller busy time, unsafe shutdowns, error-log entry count, and OCP C0h fields unless mapped to an explicit grading rule.

#### NVMe OCP C0h Extended Telemetry

For **datacenter-class NVMe SSDs**, the **OCP Datacenter NVMe SSD Specification** defines the **SMART / Health Information Extended** log page (**log identifier C0h**, 512-byte page) in **Section 4.8.6**. The authoritative source is the OCP publication; a Markdown copy is kept in-repo for convenience:

- **Official (PDF):** [Datacenter NVMe SSD Specification v2.7 Final](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1) (Open Compute Project)
- **Local copy:** [`docs/Datacenter NVMe SSD Specification v2.7 Final.md`](./Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md) — **Section 4.8.6** *SMART / Health Information Extended Log Page (Log Identifier C0h) Requirements*

CDI Health reads this page when the drive and `nvme-cli` OCP plugin support it (`nvme ocp smart-add-log` → `ocp_smart_log` on NVMe devices; surfaced in the HTML report **Advanced** view on the **NVMe SSD** tab only).

**Summary of useful C0 attributes** (requirement IDs per Section 4.8.6 — see the spec for units, normalization rules, and reserved ranges):

| ID | Field (short name) |
|----|---------------------|
| SMART-1 | Physical media units written (user + system; supports **WAF**) |
| SMART-2 | Physical media units read |
| SMART-3 | Bad user NAND blocks (normalized + raw) |
| SMART-4 | Bad system NAND blocks (normalized + raw) |
| SMART-5 | XOR recovery count |
| SMART-6 | Uncorrectable read error count |
| SMART-7 | Soft ECC error count |
| SMART-8 | End-to-end detected / corrected errors |
| SMART-9 | System data % used (system-area endurance; distinct from SLOG-4 normalization) |
| SMART-10 | Refresh counts (blocks reallocated for integrity, not GC/wear leveling) |
| SMART-11 | Min / max user data erase counts |
| SMART-12 | Thermal throttling status and event count |
| SMART-13 | DSSD specification version |
| SMART-14 | PCIe correctable error count |
| SMART-15 | Incomplete shutdowns |
| SMART-17 | % free blocks (spare pool) |
| SMART-19 | Capacitor health (PLP hold-up); `FFFFh` if no PLP |
| SMART-21 | Unaligned I/O count |
| SMART-30 | Proactive bad die retirement count |

Additional C0 fields in Section 4.8.6 include NVM Express and transport **errata** bytes (**SMART-20**, **SMART-32**, **SMART-34**, **SMART-35**), **NUSE**, endurance estimate, power-state counters, and other vendor-telemetry slots. Absence of C0h does not imply failure.

## HTML Report (Offline)

CDI Health can emit an **offline-friendly HTML** report (`cdi-health report --format html`) and a **CSV** export of the same advanced column set (`cdi-health report --format csv`) for spreadsheets and sorting.

### HTML

- **Layout:** Left navigation by **drive class** (SATA HDD, SAS HDD, SATA SSD, SAS SSD, NVMe SSD). Rows are keyed by **serial number** only (no `/dev/` paths in the table).
- **Simple view:** Score, grade, status, and one-line deductions.
- **Advanced view:** Wide table of identity, summaries, and protocol-specific columns.
- **ATA / SCSI:** Column **“SMART attributes (full JSON)”** — **ATA**: full `smart_attributes` table; **SCSI**: error counter log plus grown-defect count.
- **NVMe SSD tab:** **Health log (02h)** fields are **split into separate columns** (e.g. data units read/written, host reads/writes, controller busy time, power cycles/POH from the log, unsafe shutdowns, error log entries, warning/critical comp time, self-test current) so values can be compared and sorted without parsing JSON. A **“Full NVMe logs (JSON)”** column still carries the combined health + self-test JSON when needed.
- **OCP C0h:** Column **“OCP SMART log (JSON)”** appears **only** on the **NVMe SSD** tab. Other tabs do **not** show this column.

### CSV

- One file **per run**; first column **Report category**, then a **stable union** of all advanced headers across categories. Cells are **empty** where a column does not apply to that drive (e.g. NVMe-only columns on SATA rows).
- UTF-8 with BOM for Excel compatibility.

## Data Collection Methods

### smartctl (smartmontools)

Primary tool for collecting SMART data from ATA, NVMe, and SCSI devices.

**Usage:**
```bash
smartctl -x -j /dev/sda    # ATA device
smartctl -x -j /dev/nvme0  # NVMe device
smartctl -x -j /dev/sg0    # SCSI device
```

**Output Format:** JSON (`-j` flag)

### nvme-cli

Used for NVMe-specific operations, capacity information, and **OCP** log page **C0h** when the drive and plugin support it.

**Usage:**
```bash
nvme list -o json           # List all NVMe devices
nvme smart-log /dev/nvme0   # Get health information
nvme ocp smart-add-log /dev/nvme0n1 -o json   # OCP SMART Additional Log (C0h), optional
```

The OCP plugin must be available for decoding (verified with **nvme-cli 2.8** on Solidigm D5-P5336 122 TB drives; older builds may lack it); collected JSON is stored as **`ocp_smart_log`**.

### openSeaChest (Optional)

Enhanced tool for drive health checks and vendor-specific information. CDI primarily parses `smartctl` JSON today, but openSeaChest guidance is useful for validating interpretation:

- Use `--smartCheck` as a quick pass/fail check.
- Prefer `--deviceStatistics` for SATA drives when available because the counters are standardized and vendor-agnostic.
- Use SMART attributes when Device Statistics are unavailable or for broadly understood legacy attributes.
- Use `--showNvmeHealth` for NVMe SMART / Health Information log review.
- Use SCSI/SAS Device Statistics for SAS drives.

**Usage:**
```bash
openSeaChest_Basics --deviceInfo --device /dev/sda
openSeaChest_SMART --deviceInfo --device /dev/sda
```

## Diagnostic Workflow Guidance

The grading policy above is about the device's current disposition. When diagnosing a live device, use a conservative workflow:

1. Run a quick SMART check.
2. Inspect standardized health data where possible: Device Statistics for SATA/SAS, NVMe health log 02h for NVMe.
3. Review SMART attributes for ATA/SATA, especially when Device Statistics are unavailable.
4. Run short DST/self-test when a device shows symptoms or before important reuse decisions.
5. Run long DST/self-test when earlier checks show issues or a more thorough surface/device test is needed.
6. Re-scan after remediation attempts such as pending-sector cleanup.

Interpretation notes from openSeaChest:

- **SMART failed** means the drive exceeded manufacturer failure criteria and is a CDI hard fail-gate.
- **SMART warning** requires inspection, but is not automatically a hard fail because some warning thresholds represent lifetime counters or advisory states.
- **Unable to run SMART** is an unknown/unsupported/permission/interface condition, not a health failure by itself.
- **Pending sectors / offline uncorrectable sectors** indicate active media issues. Operational workflows may attempt cleanup/reallocation, but CDI should grade the current post-scan state; persistent or recurring defects remain health concerns.
- **DST/self-test failures** should be interpreted by failure mode. Mechanical, electrical, servo, handling-damage, or unknown hardware failures mean replace the drive. Read-element failures may correspond to media defects that can sometimes be remapped, but they still require immediate backup, remediation, and re-scan before reuse.
- **CRC errors** are often cable/controller/connection issues rather than drive media failure; use them as investigation telemetry unless a future spec revision defines a direct threshold.
- **SCSI/SAS non-medium errors and corrected-error counts** are useful trend signals. Rapid growth should trigger investigation, but CDI does not currently hard-fail on these counters alone.

## Device Statistics Log

The Device Statistics Log (DSL) provides detailed operational statistics:

### ATA Device Statistics

- **Rotating Media Statistics**: For HDDs
  - Spin-up time
  - Seek errors
  - Seek time performance
- **Temperature Statistics**: Comprehensive temperature data
  - Current, average, min/max temperatures
  - Short-term and long-term averages
- **General Statistics**: Operational metrics
  - Power-on hours
  - Power cycles
  - Load cycles

### Accessing Device Statistics

Device statistics are automatically collected via `smartctl -x` and parsed from the `ata_device_statistics` JSON structure.

## Critical Health Indicators

The class sections above are authoritative. This summary is a quick checklist:

- **All classes:** SMART failure, Operational State=Fail, and temperature above maximum operating temperature are hard fail-gates.
- **SATA HDD:** Reallocated/pending sectors at the HDD failure threshold and uncorrectable/offline-uncorrectable errors above limit are hard fail-gates.
- **SAS HDD:** Grown defects at the HDD failure threshold and combined uncorrected read/write/verify errors above limit are hard fail-gates.
- **SATA SSD:** Uncorrectable/offline-uncorrectable errors above limit and reserved space (232) at/below threshold are hard fail-gates; percentage used over threshold is a fail-gate only under `binary`.
- **SAS SSD:** Combined uncorrected read/write/verify errors above limit are hard fail-gates; percentage used over threshold is a fail-gate only under `binary`.
- **NVMe SSD:** Non-zero critical warning, non-zero media/data-integrity errors, and available spare below AVSPT are hard fail-gates; self-test failures per profile; percentage used over threshold is a fail-gate only under `binary`.
- **Telemetry-only unless otherwise specified:** POH, power cycles, load cycles, data units read/written, unsafe shutdown count, non-medium errors, and OCP C0h extended fields.

## Thresholds and Limits

Default thresholds (configurable via `src/cdi_health/config/thresholds.yaml`):

### SATA HDD
- Maximum reallocated sectors: **10** (`ata.maximum_reallocated_sectors`)
- Maximum pending sectors: **10** (`ata.maximum_pending_sectors`)
- HDD sector grading: concern threshold **2**, max deduction per metric **10** (`grading.hdd_sector_concern_threshold`, `grading.hdd_sector_defect_max_deduction_points`)
- Maximum uncorrectable/offline-uncorrectable errors: **10**

### SAS HDD
- Maximum grown defects: **10** (`scsi.maximum_grown_defects`)
- HDD sector grading: same concern/excess curve as SATA HDD
- Maximum combined uncorrected read/write/verify errors: **10** (`scsi.maximum_uncorrected_errors`)

### SATA SSD
- SSD percentage used: points-only from **80%**; at/past **100%** → C (D with other warnings) under `abcdf`
- Reserved space (232): same bands as NVMe available spare
- Maximum uncorrectable/offline-uncorrectable errors: **10**
- Reallocated/pending counts use SSD-style per-defect handling, not the HDD sector curve

### SAS SSD
- SSD percentage used: points-only from **80%**; at/past **100%** → C (D with other warnings) under `abcdf`
- Maximum combined uncorrected read/write/verify errors: **10** (`scsi.maximum_uncorrected_errors`)
- Grown defects, if reported for an SSD, use SSD-style per-defect handling

### NVMe SSD
- Percentage used: −5 at **80%**, −10 at **90%**; at/past **100%** (`maximum_percentage_used`) → C, or D with other warnings (`endurance_exceeded_grade`)
- Maximum media/data-integrity errors: **0**
- Critical warning: must be **0**
- Available spare: A ≥ **80%**, B ≥ **60%**, C ≥ **40%**, D ≥ AVSPT, F < AVSPT (drive-reported threshold, or CDI fallback **10%** when none is reported)
- Self-test: failures (results 5–7) graded by recency under `abcdf`; any failure is F under `binary`
- **OCP C0h** (optional): When present, see **Section 4.8.6** in the [OCP Datacenter NVMe SSD Specification v2.7 PDF](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1) (or the [local Markdown copy](./Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md)) for field definitions; CDI stores raw JSON in `ocp_smart_log`

## Certification Criteria

**`abcdf` (default):** certification is tri-state (§12.7). Grades **A, B, C** are **certified**, **D** is **Advisory** (limited reuse), **F** is **not certified**. UNGRADED drives are not certified. Because every fail-gate forces F, a certified drive has by construction: SMART pass, operational state not Fail, no critical errors, temperature within range, NVMe critical warning and media errors clear, and available spare at or above AVSPT. An SSD at/past rated endurance with no other warnings grades C and is therefore certified for non-critical reuse; `recommended_use` reports the intended tier.

**`binary`:** a device is **CDI Certified** when its grade is **A or B** (score ≥ 75) with no critical deductions — which additionally requires percentage used ≤ 100% and no failed self-test.

## References

- [OCP Datacenter NVMe SSD Specification v2.7 (official PDF)](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1) — **Section 4.8.6** (C0h extended SMART)
- [Datacenter NVMe SSD Specification v2.7 — local Markdown copy](./Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md) (same content, in-repo)
- [SMART Standard](https://en.wikipedia.org/wiki/S.M.A.R.T.)
- [NVMe Specification](https://nvmexpress.org/specifications/)
- [SCSI Standards](https://www.t10.org/)
- [openSeaChest Drive Health and SMART](https://github.com/Seagate/openSeaChest/wiki/Drive-Health-and-SMART)
- [openSeaChest How To Check Drive Health](https://github.com/Seagate/openSeaChest/wiki/How-To-Check-Drive-Health)
- [openSeaChest Documentation](https://github.com/Seagate/openSeaChest/wiki)
- [smartmontools Documentation](https://www.smartmontools.org/)
