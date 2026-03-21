# CDI Health Specification

## Overview

The Circular Drive Initiative (CDI) Health Scanner provides a standardized method for assessing storage device health across different protocols: ATA/SATA, NVMe, and SCSI/SAS. This document describes how health assessment works for each protocol type.

## Health Scoring System

### Score Calculation

Health scores range from 0-100, calculated based on multiple factors:

- **SMART Status**: Pass/Fail (critical)
- **Reallocated Sectors**: Count of reallocated sectors
- **Pending Sectors**: Count of sectors pending reallocation
- **Uncorrectable Errors**: Count of uncorrectable read/write errors
- **Temperature**: Operating temperature vs. maximum rated temperature
- **Percentage Used**: Wear level indicator (SSDs only)
- **Critical Warnings**: NVMe-specific critical warning flags
- **Media Errors**: NVMe-specific media error count

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

#### Percentage Used (Wear Level) - Vendor Specific

SATA SSDs report wear level through vendor-specific SMART attributes:

- **Attribute 231**: Wear Leveling Count (some vendors report percentage used directly)
- **Attribute 177**: Wear Leveling Count (Samsung - reports remaining life, calculate: 100 - value)
- **Attribute 169**: Remaining Life (some vendors - calculate: 100 - value)
- **Attribute 202**: Percentage Used (some vendors - direct percentage)
- **Attribute 232**: Available Reserved Space (Intel - indicates wear indirectly)

The tool attempts to extract percentage used from these attributes, falling back to "-" if not available.

#### Device Statistics Log

ATA devices provide a Device Statistics log containing:
- **Rotating Media Statistics**: For HDDs (spin-up time, seek errors, etc.)
- **Temperature Statistics**: Current, average, min/max temperatures
- **General Statistics**: Power-on hours, power cycles, etc.

#### Health Assessment Criteria

- **SMART Status**: Must pass
- **Reallocated Sectors**: Threshold typically 50 sectors
- **Pending Sectors**: Threshold typically 10 sectors
- **Uncorrectable Errors**: Threshold typically 10 errors
- **Temperature**: Must not exceed maximum operating temperature
- **Percentage Used**: Threshold typically 100% (varies by vendor)

### NVMe Devices

NVMe devices use the NVMe Health Information Log for health monitoring.

#### Key Health Metrics

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

#### Health Information Log Structure

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

- **Grown Defects**: Threshold typically 50 defects
- **Uncorrected Errors**: Combined read/write/verify errors, threshold typically 10
- **SMART Status**: Must pass
- **Temperature**: Must not exceed maximum operating temperature

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

Used for NVMe-specific operations and capacity information.

**Usage:**
```bash
nvme list -o json           # List all NVMe devices
nvme smart-log /dev/nvme0   # Get health information
```

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
2. **Reallocated/Grown Defects**: Low count indicates good health
3. **Uncorrectable Errors**: Should be zero
4. **Temperature**: Within operating range

### Protocol-Specific Indicators

#### ATA/SATA
- **Pending Sectors**: Sectors waiting for reallocation
- **Percentage Used**: Wear level for SSDs (vendor-specific)

#### NVMe
- **Critical Warning Flags**: Multiple warning conditions
- **Percentage Used**: Standardized wear level indicator
- **Media Errors**: Data integrity errors

#### SCSI/SAS
- **Grown Defects**: Similar to reallocated sectors
- **Error Counter Log**: Detailed read/write/verify errors

## Thresholds and Limits

Default thresholds (configurable via YAML config):

### ATA Devices
- Maximum Reallocated Sectors: 50
- Maximum Pending Sectors: 10
- Maximum Uncorrectable Errors: 10
- Maximum SSD Percentage Used: 100%

### NVMe Devices
- Maximum Percentage Used: 100%
- Maximum Media Errors: 0 (any errors are concerning)
- Critical Warning: Must be 0

### SCSI Devices
- Maximum Grown Defects: 50
- Maximum Uncorrected Errors: 10

## Certification Criteria

A device is considered **CDI Certified** (suitable for reuse) if:

1. Health Score ≥ 75 (Grade B or better)
2. SMART Status: Pass
3. No critical errors (reallocated/pending/uncorrectable within thresholds)
4. Temperature within operating range
5. Percentage Used < 100% (for SSDs)

## References

- [SMART Standard](https://en.wikipedia.org/wiki/S.M.A.R.T.)
- [NVMe Specification](https://nvmexpress.org/specifications/)
- [SCSI Standards](https://www.t10.org/)
- [openSeaChest Documentation](https://github.com/Seagate/openSeaChest/wiki)
- [smartmontools Documentation](https://www.smartmontools.org/)
