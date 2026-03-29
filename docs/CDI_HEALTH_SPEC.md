# CDI Health Specification

## Overview

The Circular Drive Initiative (CDI) Health Scanner provides a standardized method for assessing storage device health across **ATA/SATA**, **NVMe**, and **SCSI/SAS**. This document describes scoring, thresholds, data collection, **offline HTML reporting**, and how **NVMe log page 02h** (baseline health) relates to **OCP log page C0h** (extended datacenter telemetry).

**Fleet grouping:** Devices are classified for reporting and analysis by **transport** and **media** (for example SATA HDD, SAS HDD, SATA SSD, SAS SSD, NVMe SSD), using `transport_protocol`, `media_type` (HDD vs SSD), and `interface_link` where applicable.

## Health Scoring System

### Score Calculation

Health scores range from **0–100** (starting at 100). The calculator applies deductions for failed checks. Typical inputs include:

- **SMART Status**: Pass/Fail (critical)
- **Reallocated Sectors** (SATA): Count of reallocated sectors (**HDD sector curve** below)
- **Pending Sectors** (SATA): Count of sectors pending reallocation (**HDD sector curve** below)
- **Grown Defects** (SAS/SCSI): Same **numeric policy** as SATA HDD reallocated/pending (**HDD sector curve** below)
- **Uncorrectable Errors**: Uncorrectable read/write (ATA) and combined uncorrected errors (SCSI)
- **Temperature**: Operating temperature vs. maximum rated temperature
- **Percentage Used**: Wear level (SSDs)
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

**Example (defaults C=2, F=10, M=10, E=1, E_cap=40):** count **5** → raw **(5−2)/(10−2)×10 ≈ 3.75** → **4** points; count **10** → **10** points (no excess yet), critical; count **48** → **10 + min(40, 38) = 48** points, critical.

Other deductions in the same 0–100 model include failed **SMART** status, failed **NVMe self-test**, **temperature** warning/critical bands, **SSD percentage used** over threshold, and **per-error** uncorrectable handling — see `src/cdi_health/classes/scoring.py` and `src/cdi_health/config/thresholds.yaml` for the full ruleset.

### Grade Assignment

- **A (90-100)**: Excellent - Drive is healthy and suitable for reuse
- **B (75-89)**: Good - Minor issues detected
- **C (60-74)**: Fair - Some degradation present
- **D (40-59)**: Poor - Significant issues detected
- **F (0-39)**: Failed - Drive should not be reused

## Protocol-Specific Implementation

### ATA/SATA Devices

ATA/SATA devices use the SMART (Self-Monitoring, Analysis, and Reporting Technology) standard for health monitoring.

#### Key SMART Attributes

- **Attribute 5**: Reallocated Sectors Count
- **Attribute 197**: Current Pending Sector Count
- **Attribute 198**: Offline Uncorrectable Sector Count
- **Attribute 4**: Start/Stop Count
- **Attribute 12**: Power Cycle Count
- **Attribute 193**: Load Cycle Count

**HDDs: SMART attributes vs Device Statistics Log**

- **Sector defect counts** used for **grading** (reallocated, pending, offline uncorrectable) come from the **ATA SMART attribute table** (`ata_smart_attributes` / standard SMART IDs above), not from the Device Statistics Log.
- **HDD-specific operational telemetry** (mechanical behavior and thermal context) is taken primarily from the **Device Statistics Log** — in particular **Rotating Media Statistics** (e.g. spin-up, seek errors, seek time) and **Temperature Statistics** (current, min/max, specified operating limits), plus **General Statistics** where present. CDI parses these from `ata_device_statistics` in the `smartctl -x -j` JSON.

#### Percentage Used (Wear Level) - Vendor Specific

SATA SSDs report wear level through vendor-specific SMART attributes:

- **Attribute 231**: Wear Leveling Count (some vendors report percentage used directly)
- **Attribute 177**: Wear Leveling Count (Samsung - reports remaining life, calculate: 100 - value)
- **Attribute 169**: Remaining Life (some vendors - calculate: 100 - value)
- **Attribute 202**: Percentage Used (some vendors - direct percentage)
- **Attribute 232**: Available Reserved Space (Intel - indicates wear indirectly)

The tool attempts to extract percentage used from these attributes, falling back to "-" if not available.

#### Device Statistics Log

The Device Statistics Log complements the SMART attribute table. For **SSDs**, CDI also uses the **Solid State Device Statistics** page (e.g. percentage-used endurance) when available. For **HDDs**, the emphasis is **rotating media** and **temperature** pages as above.

ATA devices can expose:
- **Rotating Media Statistics**: For HDDs (spin-up time, seek errors, etc.)
- **Temperature Statistics**: Current, average, min/max temperatures
- **General Statistics**: Power-on hours, power cycles, etc.

#### Health Assessment Criteria

- **SMART Status**: Must pass
- **HDD sector defects (SATA reallocated / pending)**
  Use the **HDD sector defect curve** above. Defaults: `grading.hdd_sector_concern_threshold` (**2**), `ata.maximum_reallocated_sectors` / `ata.maximum_pending_sectors` (**10**), `grading.hdd_sector_defect_max_deduction_points` (**10**). **SSDs** use percentage-used and uncorrectable / offline-uncorrectable handling instead of this curve for wear.
- **Uncorrectable Errors**: Threshold typically 10 errors
- **Temperature**: Must not exceed maximum operating temperature
- **Percentage Used**: Threshold typically 100% (varies by vendor)

### NVMe Devices

NVMe devices use the **SMART / Health Information** log page (**log identifier 02h**) from `smartctl` / the NVMe specification for baseline health. **Optional** **OCP** log page **C0h** (extended) is described below and in the OCP Datacenter NVMe SSD Specification.

#### Key Health Metrics (log page 02h)

- **Critical Warning**: Bit flags indicating critical conditions
  - Bit 0: Available spare below threshold
  - Bit 1: Temperature exceeds threshold
  - Bit 2: Reliability degraded
  - Bit 3: Read-only mode
  - Bit 4: Volatile memory backup device failed
- **Percentage Used**: Endurance indicator (0-100%)
- **Media Errors**: Count of media and data integrity errors
- **Power On Hours**: Total power-on time
- **Data Units Written**: Total data written (for wear calculation)

#### OCP SMART / Health Information Extended (log page C0h)

For **datacenter-class NVMe SSDs**, the **OCP Datacenter NVMe SSD Specification** defines the **SMART / Health Information Extended** log page (**log identifier C0h**, 512-byte page) in **Section 4.8.6**. The authoritative source is the OCP publication; a Markdown copy is kept in-repo for convenience:

- **Official (PDF):** [Datacenter NVMe SSD Specification v2.7 Final](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1) (Open Compute Project)
- **Local copy:** [`docs/Datacenter NVMe SSD Specification v2.7 Final.md`](./Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md) — **Section 4.8.6** *SMART / Health Information Extended Log Page (Log Identifier C0h) Requirements*

CDI Health reads this page when the drive and `nvme-cli` OCP plugin support it (`nvme ocp smart-add-log` → `ocp_smart_log` on NVMe devices; surfaced in the HTML report **Advanced** view on the **NVMe SSD** tab only).

**Summary of critical C0 attributes** (requirement IDs per Section 4.8.6 — see the spec for units, normalization rules, and reserved ranges):

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

Additional C0 fields in Section 4.8.6 include NVM Express and transport **errata** bytes (**SMART-20**, **SMART-32**, **SMART-34**, **SMART-35**), **NUSE**, endurance estimate, power-state counters, and other vendor-telemetry slots — see the full table in the specification.

**Baseline vs extended:** Log **02h** (*SMART / Health Information*) is the standard health page used for grading (critical warning, percentage used, media errors, etc.). Log **C0h** adds extended datacenter telemetry; absence of C0h does not imply failure.

#### Health Information Log Structure (log page 02h)

The full parsed structure is stored on the device record as **`nvme_smart_health_information_log`** (for reporting and HTML exports) in addition to the scalar fields used for grading.

```json
{
  "critical_warning": 0,
  "temperature": 35,
  "available_spare": 100,
  "available_spare_threshold": 10,
  "percentage_used": 4,
  "data_units_read": 123456789,
  "data_units_written": 987654321,
  "host_reads": 123456,
  "host_writes": 987654,
  "media_errors": 0,
  "num_err_log_entries": 0
}
```

#### Health Assessment Criteria

These criteria apply to **log 02h** (and derived fields), not to **C0h**.

- **Critical Warning**: Must be 0
- **Percentage Used**: Threshold typically 100%
- **Media Errors**: Threshold typically 0 (any errors are concerning)
- **Available Spare**: Must be above threshold
- **Temperature**: Must not exceed warning threshold

### SCSI/SAS Devices

SCSI/SAS devices use the SCSI Log Pages and SMART data for health monitoring.

#### Key Metrics

- **Grown Defects**: Count of grown defects (similar to reallocated sectors)
- **Read Errors**: Uncorrected read errors
- **Write Errors**: Uncorrected write errors
- **Verify Errors**: Uncorrected verify errors
- **Power On Hours**: Total power-on time

#### Error Counter Log

SCSI devices provide an Error Counter Log with:
- **Read Errors**: Total uncorrected read errors
- **Write Errors**: Total uncorrected write errors
- **Verify Errors**: Total uncorrected verify errors

#### Health Assessment Criteria

- **HDD grown defects (SAS/SCSI HDDs)**
  **Grown defect count** uses the **same HDD sector defect curve** as SATA reallocated/pending (see [HDD sector defect curve (SATA and SAS)](#hdd-sector-defect-curve-sata-and-sas)). Configure **`scsi.maximum_grown_defects`** (default **10**) and the same **`grading.hdd_sector_*`** keys as for SATA.
- **Uncorrected Errors**: Combined read/write/verify errors, threshold typically 10
- **SMART Status**: Must pass
- **Temperature**: Must not exceed maximum operating temperature

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

Enhanced tool for ATA/SATA devices, provides additional vendor-specific information.

**Usage:**
```bash
openSeaChest_Basics --deviceInfo --device /dev/sda
openSeaChest_SMART --deviceInfo --device /dev/sda
```

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

### Universal Indicators (All Protocols)

1. **SMART Status**: Must pass
2. **HDD sector-equivalent defects** (SATA reallocated/pending, SAS grown defects): **≤ concern threshold** is acceptable for grading; **at or above failure threshold** is critical (see **HDD sector defect curve**)
3. **Uncorrectable Errors**: Should be zero (within configured thresholds)
4. **Temperature**: Within operating range

### Protocol-Specific Indicators

#### ATA/SATA
- **Pending Sectors**: Sectors waiting for reallocation (HDD: graded with reallocated)
- **Percentage Used**: Wear level for SSDs (vendor-specific)

#### NVMe
- **Critical Warning Flags** (log **02h**): Multiple warning conditions
- **Percentage Used** (log **02h**): Standardized wear level indicator
- **Media Errors** (log **02h**): Data integrity errors
- **C0h (optional)**: Extended OCP metrics — see the **OCP SMART / Health Information Extended (log page C0h)** subsection under NVMe and **Section 4.8.6** in the [OCP Datacenter NVMe SSD Specification v2.7 PDF](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1)

#### SCSI/SAS
- **Grown Defects**: HDD equivalent of reallocated sectors (same curve as SATA HDD)
- **Error Counter Log**: Detailed read/write/verify errors

## Thresholds and Limits

Default thresholds (configurable via `src/cdi_health/config/thresholds.yaml`):

### ATA Devices
- **Maximum Reallocated Sectors (HDD failure threshold)**: 10 (`ata.maximum_reallocated_sectors`)
- **Maximum Pending Sectors (HDD failure threshold)**: 10 (`ata.maximum_pending_sectors`)
- **HDD sector grading**: concern threshold **2**, max deduction per metric **10** (`grading.hdd_sector_concern_threshold`, `grading.hdd_sector_defect_max_deduction_points`)
- Maximum Uncorrectable Errors: 10
- Maximum SSD Percentage Used: 100%

### NVMe Devices
- Maximum Percentage Used: 100%
- Maximum Media Errors: 0 (any errors are concerning)
- Critical Warning: Must be 0
- **OCP C0h** (optional): When present, see **Section 4.8.6** in the [OCP Datacenter NVMe SSD Specification v2.7 PDF](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1) (or the [local Markdown copy](./Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md)) for field definitions; CDI stores raw JSON in `ocp_smart_log`

### SCSI Devices
- **Maximum Grown Defects (HDD failure threshold)**: 10 (`scsi.maximum_grown_defects`), with the same **0–2 / 3–9 / 10** HDD grading curve as ATA reallocated/pending
- Maximum Uncorrected Errors: 10

## Certification Criteria

A device is considered **CDI Certified** (suitable for reuse) if:

1. Health Score ≥ 75 (Grade B or better)
2. SMART Status: Pass
3. No critical errors (HDD reallocated/pending/grown-defect counts below failure thresholds; uncorrectable errors within limits)
4. Temperature within operating range
5. Percentage Used < 100% (for SSDs)

## References

- [OCP Datacenter NVMe SSD Specification v2.7 (official PDF)](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1) — **Section 4.8.6** (C0h extended SMART)
- [Datacenter NVMe SSD Specification v2.7 — local Markdown copy](./Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md) (same content, in-repo)
- [SMART Standard](https://en.wikipedia.org/wiki/S.M.A.R.T.)
- [NVMe Specification](https://nvmexpress.org/specifications/)
- [SCSI Standards](https://www.t10.org/)
- [openSeaChest Documentation](https://github.com/Seagate/openSeaChest/wiki)
- [smartmontools Documentation](https://www.smartmontools.org/)
