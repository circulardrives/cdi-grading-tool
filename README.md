# CDI Health — Storage Device Grading Toolkit

Open-source toolkit from the **Circular Drive Initiative** for scanning storage devices, computing **0–100 health scores** with **A–F grades**, and producing **offline HTML/PDF reports** and **CSV exports** suitable for reuse and circularity programs.

Supports **ATA/SATA**, **NVMe**, and **SCSI/SAS** on Linux with `smartctl`, `nvme-cli`, and related tools.

#### Operating systems

[![linux](https://img.shields.io/badge/Debian-A81D33?style=flat&logo=debian&logoColor=white)](https://www.debian.com)
[![linux](https://img.shields.io/badge/Ubuntu-E95420?style=flat&logo=ubuntu&logoColor=white)](https://www.ubuntu.com)

#### Python

[![python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)

---

## Highlights

| Area | What you get |
|------|----------------|
| **Protocols** | ATA/SATA, NVMe, SCSI/SAS; optional `openSeaChest` for extra ATA vendor data |
| **HDD grading** | Configurable curve for reallocated / pending (SATA) and grown defects (SAS): concern threshold, failure at **10** sectors/defects, max deduction per metric — see [docs/CDI_HEALTH_SPEC.md](docs/CDI_HEALTH_SPEC.md) |
| **NVMe** | Health from log **02h**; optional **OCP** log **C0h** via `nvme ocp smart-add-log` when the drive supports it ([OCP Datacenter NVMe SSD Specification v2.7 PDF](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1)) |
| **Reports** | **HTML** (tabbed by drive class, serial-keyed rows) and **PDF**; **CSV** (`report --format csv`) with the same advanced columns for Excel/sorting; NVMe **Advanced** view splits **health log 02h** into numeric columns plus optional full JSON and **OCP on NVMe tab only** |
| **CLI** | `scan`, `report`, `watch`, `selftest` (NVMe); YAML thresholds, mock data for CI |
| **API** | Optional FastAPI backend for technician dashboards (`cdi-health-api`) |

---

## Requirements

- **OS:** Linux (x86_64), privileged access to block devices for real hardware scans  
- **Python:** 3.10+

### Required tools (typical install)

```sh
sudo apt install smartmontools nvme-cli
```

**SCSI/SAS:** also install `sg3-utils` (`sg_map`, `sg_turs`, etc.).

**Optional**

- **OCP NVMe extended SMART (C0h):** `nvme-cli` **2.10+** with the OCP plugin (`nvme ocp smart-add-log`).  
- **ATA extras:** [openSeaChest](https://github.com/Seagate/openSeaChest).  
- **PDF reports:** `pip install weasyprint` (or your distro package).

---

## Installation

**From PyPI**

```shell
pip install cdi-health
```

**From source**

```shell
git clone https://github.com/circulardrives/cdi-grading-tool.git
cd cdi-grading-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
# optional: dev tools, API server, PDF
pip install -e .[dev,api]
```

---

## Quick start

```shell
# Fleet scan — detailed table (default)
sudo cdi-health scan

# One device, compact table
sudo cdi-health scan --device /dev/nvme0 --no-details

# JSON for scripting
sudo cdi-health scan -o json

# HTML report (mock-friendly, no hardware)
cdi-health report --format html --mock-data src/cdi_health/mock_data

# Continuous monitoring
sudo cdi-health watch --interval 60

# NVMe self-tests (requires nvme-cli)
sudo cdi-health selftest
```

Custom thresholds:

```shell
sudo cdi-health scan --config /path/to/thresholds.yaml
```

Default thresholds live in [`src/cdi_health/config/thresholds.yaml`](src/cdi_health/config/thresholds.yaml).

---

## Health scoring (summary)

- **Base:** 100 points; deductions for SMART failures, temperatures, wear, uncorrectables, NVMe critical warnings/media errors, failed self-tests, etc.  
- **HDDs (SATA / SAS):** Reallocated, pending, and grown defects use a shared **concern → failure** curve (defaults: no deduction **≤2**, failure threshold **10**, up to **10** points deducted per metric at failure). **Defect counts** come from **ATA SMART attributes** / SCSI equivalents; **HDD mechanical/thermal** detail is largely from the **Device Statistics Log** — full detail in the spec.  
- **SSDs / NVMe:** Wear, media errors, critical warning bits, and related rules are documented in **[CDI Health Specification](docs/CDI_HEALTH_SPEC.md)**.

**Grades:** A 90–100 · B 75–89 · C 60–74 · D 40–59 · F 0–39.

---

## HTML, PDF, and CSV reports

```shell
sudo cdi-health report --format html --output-file report.html
sudo cdi-health report --format pdf --output-file report.pdf   # needs weasyprint
cdi-health report --format csv --output-file report.csv --mock-data src/cdi_health/mock_data
```

**CSV** is UTF-8 with BOM (Excel-friendly). The first column is **Report category**; headers are the **union** of all advanced columns (NVMe health-log fields appear as their own sortable columns). Cells are empty where a column does not apply to that drive category.

Reports group drives by **SATA HDD**, **SAS HDD**, **SATA SSD**, **SAS SSD**, **NVMe SSD**; rows use **serial number** (no `/dev/` in the main tables). **Simple** view shows score and deductions; **Advanced** adds columns including **SMART attributes (full JSON)**. The **OCP SMART log** column appears **only** on the **NVMe SSD** tab.

---

## CLI overview

| Command | Purpose |
|---------|---------|
| `cdi-health scan` | Table / JSON / CSV / YAML; `--device`, `--details` / `--no-details`, `--ignore-*`, `--mock-data`, `--config` |
| `cdi-health report` | `--format html`, `pdf`, or `csv`; `--output-file`; same discovery flags as scan |
| `cdi-health watch` | Periodic rescan (`--interval`) |
| `cdi-health selftest` | NVMe short/extended tests, `--status`, `--wait`, `--abort` |

Full options: `cdi-health --help` and `cdi-health <command> --help`.

### Scan: options (reference)

```text
  -o, --output            table | json | csv | yaml
  --details, --no-details detailed vs basic columns (table only; default --details)
  --device PATH           filter to one scanned device (NVMe namespace/controller aliases)
  --config FILE           YAML thresholds
  --mock-data / --mock-file   development & CI without hardware
```

### Self-test (NVMe)

Short tests are default; extended tests can run a long time. Requires `nvme` in `PATH`.

```shell
sudo cdi-health selftest --device /dev/nvme0 --status
sudo cdi-health selftest --wait
```

---

## Local API (optional)

Technician dashboards can use the bundled FastAPI app.

```shell
pip install -e .[api]
sudo cdi-health-api --host 127.0.0.1 --port 8844
```

Optional: `--api-token …` and header `X-API-Token`. Endpoints include `/api/v1/scan`, `/api/v1/devices`, `/api/v1/reports`, `/api/v1/selftests`, `/api/v1/jobs`. See [docs/DASHBOARD_API.md](docs/DASHBOARD_API.md).

A Next.js dashboard scaffold lives under `dashboard/` (`npm install && npm run dev`).

---

## Documentation

| Doc | Contents |
|-----|----------|
| **[CDI Health Specification](docs/CDI_HEALTH_SPEC.md)** | Scoring, HDD curve, NVMe 02h vs OCP C0h, thresholds, certification, HTML report behavior |
| **[Datacenter NVMe SSD Specification v2.7](docs/Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md)** | Local copy; authoritative **[OCP PDF](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1)** |
| **[Development](DEVELOPMENT.md)** | Style, tests, workflow |
| **[Testing](README_TESTING.md)** | Mock data and test commands |
| **[Contributing](CONTRIBUTING.md)** | Contributions |
| **[Technician deployment](docs/TECHNICIAN_DEPLOYMENT.md)** | systemd, sudoers |

---

## Features

- Multi-protocol scanning and grading  
- Configurable YAML thresholds  
- Mock JSON fixtures for development and CI  
- NVMe self-test integration  
- Offline HTML/PDF reports with CDI branding; CSV export with advanced columns  
- Watch mode and optional REST API  
- Detailed spec documentation aligned with implementation  

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

---

## Acknowledgments

Circular Drive Initiative; contributors; **smartmontools**, **nvme-cli**, **openSeaChest**, and the wider open-source ecosystem.

---

## Contact

- Nick Hayhurst — [nick.hayhurst@interactdc.com](mailto:nick.hayhurst@interactdc.com)  
- Jonmichael Hands — [jm@circulardrives.org](mailto:jm@circulardrives.org)  

**Repository:** [github.com/circulardrives/cdi-grading-tool](https://github.com/circulardrives/cdi-grading-tool)
