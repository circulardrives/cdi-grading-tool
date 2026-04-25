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

Other deductions in the same 0–100 model include failed **NVMe self-test**, **temperature** warning/critical bands, **SSD percentage used** over threshold, and **per-error** uncorrectable handling — see `src/cdi_health/classes/scoring.py` and `src/cdi_health/config/thresholds.yaml` for the full ruleset. Critical severity is a disposition-level fail-gate: it sets score **0** and grade **F** regardless of other telemetry. Warning/info deductions remain numeric and can produce A-D grades.

### Grade Assignment

- **A (90-100)**: Excellent - Drive is healthy and suitable for reuse
- **B (75-89)**: Good - Minor issues detected
- **C (60-74)**: Fair - Some degradation present
- **D (40-59)**: Poor - Significant issues detected
- **F (0-39)**: Failed - Drive should not be reused

Hard fail-gates override numeric deductions and always produce **F / score 0**:

- SMART explicitly reports failure (`false`, `failed`, `bad`, etc.)
- The scan/disposition path marks the device operational state as **Fail**
- NVMe self-test history contains a failed self-test
- NVMe critical warning is non-zero
- NVMe media/data-integrity error count is non-zero
- NVMe available spare is below the drive-reported threshold (or CDI configured fallback when no drive threshold is reported)
- SSD percentage used exceeds the CDI threshold
- HDD/SAS defect counts reach the configured failure threshold, uncorrectable errors exceed limit, or temperature exceeds operating maximum

Unknown or unavailable SMART data alone is not a hard fail unless paired with failed operational state evidence. For example, an unresponsive/DOA device reported as **State=Fail** with unknown SMART is **F**, while a device with missing SMART data but no failed-state evidence is left to other telemetry and policy.

**Power-on hours (POH):** POH is collected and reported for ATA, NVMe, and SCSI/SAS devices. It is contextual telemetry, not currently a direct grade threshold or certification criterion. HDD age may correlate with mechanical wear, but CDI grading should use explicit failure/defect indicators unless a future spec revision defines an age-based policy. For SSDs, endurance indicators such as **Percentage Used** are the grading signal rather than POH.

## Drive-Class Health Rules

Use these sections as the primary grading reference. The report uses the same five classes: **SATA HDD**, **SAS HDD**, **SATA SSD**, **SAS SSD**, and **NVMe SSD**.

### Shared Rules

These rules apply to every drive class:

- **SMART status must pass.** Explicit failure (`false`, `failed`, `bad`, etc.) is a hard fail-gate.
- **Operational State must not be Fail.** A failed scan/disposition state is a hard fail-gate even when SMART is unavailable or unknown.
- **Temperature must remain within operating range.** Exceeding the maximum operating temperature is a hard fail-gate; warning temperature is a warning deduction.
- **Power-on hours are telemetry.** POH is collected and reported, but it is not currently a direct grade threshold or certification criterion.
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

- SSD percentage used / endurance drives wear scoring when normalized data is available.
- Reallocated or pending defect counts, when present, use SSD-style per-sector handling rather than the HDD sector defect curve.
- Offline uncorrectable sectors use per-error uncorrectable handling.
- Temperature warning/critical bands apply.

**Hard-fails:**

- SMART failure.
- Operational State=Fail.
- SSD percentage used exceeds the CDI threshold.
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

- SSD percentage used / endurance drives wear scoring when normalized data is available.
- Combined uncorrected read/write/verify errors use per-error uncorrectable handling.
- Grown defects, if reported for an SSD, use SSD-style per-defect handling rather than the HDD defect curve.
- Temperature warning/critical bands apply.

**Hard-fails:**

- SMART failure.
- Operational State=Fail.
- SSD percentage used exceeds the CDI threshold when normalized data is available.
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

- Percentage used / endurance.
- Available spare compared to the drive-reported threshold; CDI uses its configured fallback only when the drive does not report a threshold.
- Temperature warning/critical bands.
- NVMe self-test result.

**Hard-fails:**

- SMART failure.
- Operational State=Fail.
- Critical warning is non-zero.
- Media/data-integrity error count is non-zero.
- Available spare is below threshold.
- Percentage used exceeds the CDI threshold.
- Any reported failed NVMe self-test. CDI accepts both `entries[].result` and smartctl `table[].self_test_result.value` shapes.
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

The OCP plugin (for example **nvme-cli** 2.10+) must be available for decoding; collected JSON is stored as **`ocp_smart_log`**.

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
- **SATA SSD:** Percentage used over threshold and uncorrectable/offline-uncorrectable errors above limit are hard fail-gates.
- **SAS SSD:** Percentage used over threshold, when normalized data is available, and combined uncorrected read/write/verify errors above limit are hard fail-gates.
- **NVMe SSD:** Non-zero critical warning, non-zero media/data-integrity errors, available spare below threshold, percentage used over threshold, and any failed self-test are hard fail-gates.
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
- Maximum SSD percentage used: **100%**
- Maximum uncorrectable/offline-uncorrectable errors: **10**
- Reallocated/pending counts use SSD-style per-defect handling, not the HDD sector curve

### SAS SSD
- Maximum SSD percentage used: **100%**
- Maximum combined uncorrected read/write/verify errors: **10** (`scsi.maximum_uncorrected_errors`)
- Grown defects, if reported for an SSD, use SSD-style per-defect handling

### NVMe SSD
- Maximum percentage used: **100%**
- Maximum media/data-integrity errors: **0**
- Critical warning: must be **0**
- Available spare: must be at or above the drive-reported threshold, or CDI fallback threshold when no drive threshold is reported
- Failed self-test count: must be **0**
- **OCP C0h** (optional): When present, see **Section 4.8.6** in the [OCP Datacenter NVMe SSD Specification v2.7 PDF](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1) (or the [local Markdown copy](./Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md)) for field definitions; CDI stores raw JSON in `ocp_smart_log`

## Certification Criteria

A device is considered **CDI Certified** (suitable for reuse) if:

1. Health Score ≥ 75 (Grade B or better)
2. SMART Status: Pass
3. Operational State is not **Fail**
4. No critical errors (HDD reallocated/pending/grown-defect counts below failure thresholds; uncorrectable errors within limits; NVMe critical warning and media errors clear)
5. Temperature within operating range
6. Percentage Used < 100% (for SSDs)
7. NVMe available spare is at or above the drive-reported threshold when available
8. No failed NVMe self-test is reported

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
