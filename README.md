# Circular Drive Initiative - Grading Toolkit
Circular Drive Initiative - Open Source Storage Device Grading Toolkit.

#### Operating Systems

[![linux](https://img.shields.io/badge/Debian-A81D33?style=flat&logo=debian&logoColor=white)](https://www.debian.com)
[![linux](https://img.shields.io/badge/Ubuntu-E95420?style=flat&logo=ubuntu&logoColor=white)](https://www.ubuntu.com)

#### Programming Languages

[![python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)

## Getting Started

This software requires the following to launch:

* Linux GNU x86/x64
* Python 3.10+

### Required 3rd Party Software

**Minimum Required (for basic scanning):**
```sh
# nvme-cli - Required for NVMe device support
sudo apt install nvme-cli

# smartmontools - Required for SMART data collection
sudo apt install smartmontools
```

**Optional (for enhanced ATA/SCSI support):**
```sh
# sg3-utils - Optional, for SCSI device support
sudo apt install sg3-utils

# openseachest - Optional, for enhanced ATA device support
# See https://github.com/Seagate/openSeaChest for installation instructions
```

### Installation

**From PyPI (recommended for end users):**
```shell
pip install cdi-health
```

**From source (for development):**
```shell
# Clone the repository
git clone https://github.com/circulardrives/cdi-grading-tool-alpha.git
cd cdi-grading-tool

# Create a Virtual Environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install CDI Grading Tool in editable mode
pip install -e .

# Or install with development dependencies
pip install -e .[dev]
```

### Quick Start

```shell
# Scan all drives (default: detailed table output)
cdi-health scan

# Scan with verbose output
cdi-health scan -v

# Scan only NVMe devices
cdi-health scan --ignore-ata --ignore-scsi

# Output as JSON
cdi-health scan -o json

# Output as CSV
cdi-health scan -o csv
```

## Local Dashboard Backend API

The project now includes a local FastAPI backend for technician dashboards (for example, a Shadcn UI).

### Install API Dependencies

```shell
pip install -e .[api]
```

### Run API (Root Required)

Real device commands require privileged access to block devices. Run as root:

```shell
sudo cdi-health-api --host 127.0.0.1 --port 8844
```

Optional token auth for dashboard-to-backend traffic:

```shell
sudo cdi-health-api --api-token "replace-me"
```

Then send `X-API-Token: replace-me` from the dashboard client.

### API Endpoints

- `GET /api/v1/health` - Backend health and privilege/tool status
- `POST /api/v1/scan` - Run scan and return device metrics/grades
- `GET /api/v1/devices` - Return cached scan (or refresh with `?refresh=true`)
- `POST /api/v1/selftests` - Start asynchronous NVMe self-test job
- `GET /api/v1/selftests/status` - Get current self-test status
- `POST /api/v1/selftests/abort` - Abort running self-test on a device
- `GET /api/v1/jobs` - List async jobs
- `GET /api/v1/jobs/{job_id}` - Read single async job result/status
- `POST /api/v1/reports` - Generate HTML/PDF report

### Dashboard (Next.js + Shadcn-Style UI)

A local technician dashboard scaffold is included in `/dashboard`.

```shell
cd dashboard
cp .env.example .env.local
npm install
npm run dev
```

The dashboard runs on `http://127.0.0.1:3000` and proxies to the local API backend.

### Deployment Assets

- Systemd unit templates: `/deploy/systemd`
- Optional sudoers profile: `/deploy/sudoers/cdi-health-technician`
- Deployment guide: `/docs/TECHNICIAN_DEPLOYMENT.md`

## CLI Usage

### Scan Command

The `scan` command scans storage devices and displays health information in a detailed table format.

**Default Output Format:**
```
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                         CDI Health Scanner                                                         ║
╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                      Scanned: 5 devices | Healthy: 5 | Warning: 0 | Failed: 0                                      ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

┌────────────┬──────────────────────┬────────────────────┬────────────┬──────────┬──────────────┬─────────┬───────┬───────┬──────────────┐
│ Device     │ Model                │ Serial             │       Size │      POH │       Errors │   Used% │ Score │ Grade │ Status       │
├────────────┼──────────────────────┼────────────────────┼────────────┼──────────┼──────────────┼─────────┼───────┼───────┼──────────────┤
│ /dev/sda   │ MK000960GWSSD        │ S4DHNE0M203447     │     960 GB │     1.2y │            0 │       - │  100  │   A   │ ✓ Excellent  │
│ /dev/nvme0 │ SSDPEK1A118GA        │ PHOC150200JY118B   │     118 GB │     2.8y │            0 │      0% │  100  │   A   │ ✓ Excellent  │
└────────────┴──────────────────────┴────────────────────┴────────────┴──────────┴──────────────┴─────────┴───────┴───────┴──────────────┘

Legend: ✓ Healthy  ⚠ Warning  ✗ Failed
```

**Table Columns:**
- **Device**: Device path (e.g., `/dev/sda`, `/dev/nvme0`)
- **Model**: Drive model number
- **Serial**: Drive serial number
- **Size**: Drive capacity (formatted as GB/TB)
- **POH**: Power On Hours (formatted as years/days, e.g., "2.8y", "356d")
- **Errors**: Error summary (R:reallocated, P:pending, U:uncorrectable, M:media errors, CW:critical warning)
- **Used%**: Percentage used (NVMe SSDs only, shows wear level)
- **Score**: Health score (0-100)
- **Grade**: Health grade (A-F)
- **Status**: Health status with visual indicator

**Command Options:**
```shell
cdi-health scan [OPTIONS]

Options:
  -h, --help              Show help message
  -v, --verbose           Show detailed information during scan
  --no-color              Disable colored output
  --config FILE           Path to YAML config file for custom thresholds
  --mock-data PATH        Use mock data directory instead of real devices
  --mock-file FILE        Use specific mock JSON file for single device
  --ignore-ata            Ignore ATA/SATA devices
  --ignore-nvme           Ignore NVMe devices
  --ignore-scsi           Ignore SCSI devices
  -o, --output FORMAT     Output format: table (default), json, csv, yaml
  --all                   Show all device attributes (not just summary)
  --details               Show detailed table with critical stats (default)
  --device PATH           Scan specific device only
```

**Examples:**
```shell
# Basic scan of all devices
cdi-health scan

# Scan with JSON output for scripting
cdi-health scan -o json

# Scan only NVMe drives
cdi-health scan --ignore-ata --ignore-scsi

# Scan specific device
cdi-health scan --device /dev/nvme0

# Export to CSV for analysis
cdi-health scan -o csv > drive_health.csv
```

### Report Command

Generate detailed HTML or PDF health reports.

```shell
# Generate HTML report
cdi-health report --format html

# Generate PDF report
cdi-health report --format pdf

# Custom output filename
cdi-health report --format html --output-file my_report.html
```

### Watch Command

Continuously monitor device health and report changes.

```shell
# Monitor every 60 seconds (default)
cdi-health watch

# Monitor every 30 seconds
cdi-health watch --interval 30
```

### Self-Test Command

Run NVMe device self-tests to verify drive integrity. By default, finds all NVMe devices that support self-test and runs short tests.

```shell
# Run short self-tests on all supported NVMe devices (default)
cdi-health selftest

# Run extended self-tests
cdi-health selftest --type extended

# Run test on specific device
cdi-health selftest --device /dev/nvme0

# Check status of a specific device
cdi-health selftest --device /dev/nvme0 --status

# Wait for tests to complete
cdi-health selftest --wait

# Abort running test
cdi-health selftest --device /dev/nvme0 --abort
```

**Self-Test Features:**
- Automatically detects NVMe devices that support self-test (via `nvme id-ctrl`)
- Runs short self-tests by default (completes in ~2 minutes)
- Extended self-tests available (may take several hours)
- Displays results in a formatted table similar to scan output
- Shows test status, results, and completion dates
- On subsequent runs, displays existing test results instead of starting new tests

## Output Formats

### Table Format (Default)
The default table format provides a comprehensive view of all drives with critical health metrics:
- Device identification (path, model, serial)
- Capacity and size
- Power-on hours (formatted for readability)
- Error counts (reallocated, pending, uncorrectable, media errors)
- Percentage used (for NVMe SSDs)
- Health score and grade
- Status indicators

### JSON Format
Structured JSON output for programmatic access:
```shell
cdi-health scan -o json
```

### CSV Format
Comma-separated values for spreadsheet analysis:
```shell
cdi-health scan -o csv > drives.csv
```

### YAML Format
YAML output for configuration tools:
```shell
cdi-health scan -o yaml
```

## Health Scoring

The tool calculates a health score (0-100) and assigns a grade (A-F) based on:

- **SMART Status**: Pass/Fail (critical failure if failed)
- **Reallocated Sectors**: Count of reallocated sectors
- **Pending Sectors**: Count of pending reallocation sectors
- **Uncorrectable Errors**: Count of uncorrectable errors
- **Temperature**: Operating temperature vs. maximum
- **Percentage Used**: Wear level for NVMe SSDs
- **Critical Warnings**: NVMe critical warning flags
- **Media Errors**: NVMe media error count
- **Self-Test Results**: Failed NVMe self-tests result in automatic Grade F (critical failure)

**Grade Scale:**
- **A (90-100)**: Excellent - Drive is healthy and suitable for reuse
- **B (75-89)**: Good - Minor issues detected
- **C (60-74)**: Fair - Some degradation present
- **D (40-59)**: Poor - Significant issues detected
- **F (0-39)**: Failed - Drive should not be reused

**Critical Failures (Automatic Grade F):**
- Failed SMART status
- Failed NVMe self-test (short or extended)
- Critical hardware failures detected

## Documentation

### CDI Health Specification

For detailed information about how health assessment works across different protocols (ATA/SATA, NVMe, SCSI/SAS), see:

**[CDI Health Specification](docs/CDI_HEALTH_SPEC.md)**

This document covers:
- Health scoring methodology
- Protocol-specific implementation details
- SMART attribute interpretation
- Vendor-specific percentage used extraction
- Device statistics log usage
- Thresholds and certification criteria

### Development Documentation

- **[Development Guide](DEVELOPMENT.md)** - Code quality standards, testing, and development workflow
- **[Testing Guide](README_TESTING.md)** - Comprehensive testing documentation
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute to the project

## Features

### Current Features
- ✅ Multi-protocol support (ATA/SATA, NVMe, SCSI/SAS)
- ✅ Comprehensive health scoring (0-100 scale with A-F grades)
- ✅ NVMe self-test execution and monitoring
- ✅ Multiple output formats (table, JSON, CSV, YAML)
- ✅ HTML and PDF report generation
- ✅ Continuous monitoring/watch mode
- ✅ Mock data support for testing
- ✅ Configurable thresholds via YAML
- ✅ Responsive terminal output (adapts to console width)
- ✅ Failed self-test detection (automatic Grade F)

### Roadmap
- [x] Add change logs (see [CHANGELOG.md](CHANGELOG.md))
- [x] NVMe self-test support
- [ ] Enhanced reporting features
- [ ] Historical tracking
- [ ] Web interface
- [ ] ATA/SCSI self-test support
- [ ] Enhanced temperature grading
- [ ] Rate of change detection
- [ ] Performance optimizations

## Change Log

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and changes.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text.

## Acknowledgments

- Circular Drive Initiative for the vision and support
- All contributors who have helped improve this tool
- The open source community for the tools and libraries that make this possible

## Contact
* Jonmichael Hands - CDI/Chia - jmhands@chia.net
* Nick Hayhurst - Interact/Cedar - nick.hayhurst@interactdc.com
