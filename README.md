# CDI Health — Storage Device Grading Toolkit

Open-source toolkit from the **Circular Drive Initiative** for scanning storage devices, computing **0–100 health scores** with **A–F grades**, and producing **offline HTML/PDF reports** and **CSV exports** suitable for reuse and circularity programs.

Supports **ATA/SATA**, **NVMe**, and **SCSI/SAS** on Linux with `smartctl`, `nvme-cli`, and related tools.

#### Operating systems

[linux](https://www.debian.com)
[linux](https://www.ubuntu.com)

#### Python

[python](https://www.python.org)

---

## Highlights


| Area              | What you get                                                                                                                                                                                                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Drive classes** | Rules and reports are organized by **SATA HDD**, **SAS HDD**, **SATA SSD**, **SAS SSD**, and **NVMe SSD**                                                                                                                                                                     |
| **Health spec**   | Main repository spec: [docs/CDI_HEALTH_SPEC.md](docs/CDI_HEALTH_SPEC.md), including hard fail-gates, thresholds, telemetry-only fields, and openSeaChest workflow guidance                                                                                                    |
| **HDD grading**   | Configurable curve for SATA reallocated / pending sectors and SAS grown defects: concern threshold, failure at **10** sectors/defects, and critical results hard-fail to **F / score 0**                                                                                      |
| **NVMe**          | Health from log **02h**; critical warning, media/data-integrity errors, failed self-tests, percentage used, and spare threshold feed scoring. Optional **OCP** log **C0h** is extended telemetry                                                                              |
| **Reports**       | **HTML** (tabbed by drive class, serial-keyed rows) and **PDF**; **CSV** (`report --format csv`) with the same advanced columns for Excel/sorting; NVMe **Advanced** view splits **health log 02h** into numeric columns plus optional full JSON and **OCP on NVMe tab only** |
| **CLI**           | `scan`, `report`, `watch`, `selftest` (NVMe); YAML thresholds, mock data for CI                                                                                                                                                                                               |
| **API**           | Optional FastAPI backend for technician dashboards (`cdi-health-api`)                                                                                                                                                                                                         |


---

## Requirements

- **OS:** Linux (x86_64), privileged access to block devices for real hardware scans
- **Python:** 3.10+

### Required tools (typical install)

```sh
sudo apt install smartmontools nvme-cli
```

**SCSI/SAS:** also install `sg3-utils` (e.g. `sg_map26`, `sg_turs`). Mixed NVMe + SAS benches usually install all three packages together.

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

**Debian/Ubuntu `.deb` (release builds)**

Prebuilt packages attach to [GitHub Releases](https://github.com/circulardrives/cdi-grading-tool/releases). Install:

```shell
sudo dpkg -i cdi-health_*_all.deb
sudo apt-get install -f   # pull in dependencies if dpkg reported any
```

The package depends on `**python3**` and **recommends** `smartmontools` and `nvme-cli`; **suggests** `sg3-utils` for SAS. Application files live under `**/opt/cdi-health/lib`**; `**cdi-health**` and `**cdi-health-api**` are on `**PATH**` as `/usr/local/bin/...`. Bundled **openSeaChest** binaries (when included in the package) install under `/usr/local/bin`.

---

## Quick start

**Real hardware:** run `scan` / `report` / `watch` **without** `--mock-data` or `--mock-file` so the tool probes live block devices (use `sudo` when the account cannot read SMART/NVMe logs).

**Mock / CI:** pass `--mock-data path/to/mock_data` or `--mock-file path/to/fixture.json` so no hardware or elevated access is required.

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

Default thresholds live in `[src/cdi_health/config/thresholds.yaml](src/cdi_health/config/thresholds.yaml)`.

---

## Health scoring (summary)

The source of truth is the main-repo **[CDI Health Specification](docs/CDI_HEALTH_SPEC.md)**. It is organized by drive class:

- **SATA HDD:** SMART status, reallocated sectors, pending sectors, offline uncorrectable sectors, and temperature.
- **SAS HDD:** SMART status, grown defects, combined uncorrected read/write/verify errors, and temperature.
- **SATA SSD:** SMART status, normalized wear/percentage-used data when available, uncorrectable errors, and temperature.
- **SAS SSD:** SMART status, normalized endurance data when available, SCSI uncorrected errors, and temperature.
- **NVMe SSD:** SMART / Health Information log 02h, including critical warning, percentage used, available spare threshold, media/data-integrity errors, temperature, and self-test results.

**Grades:** A 90–100 · B 75–89 · C 60–74 · D 40–59 · F 0–39. Critical health signals are hard fail-gates and produce **F / score 0** regardless of remaining numeric score. POH, non-medium errors, CRC errors, OCP C0h, and many lifetime counters are reported as telemetry unless the spec defines a direct grading rule.

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


| Command               | Purpose                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------ |
| `cdi-health scan`     | Table / JSON / CSV / YAML; `--device`, `--details` / `--no-details`, `--ignore-`*, `--mock-data`, `--config` |
| `cdi-health report`   | `--format html`, `pdf`, or `csv`; `--output-file`; same discovery flags as scan                              |
| `cdi-health watch`    | Periodic rescan (`--interval`)                                                                               |
| `cdi-health selftest` | NVMe short/extended tests, `--status`, `--wait`, `--abort`                                                   |


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


| Doc                                                                                                          | Contents                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[CDI Health Specification](docs/CDI_HEALTH_SPEC.md)**                                                      | Main health spec organized by SATA HDD, SAS HDD, SATA SSD, SAS SSD, and NVMe SSD; includes scoring, hard fail-gates, thresholds, telemetry-only fields, certification, reports, and diagnostic workflow guidance |
| **[Datacenter NVMe SSD Specification v2.7](docs/Datacenter%20NVMe%20SSD%20Specification%20v2.7%20Final.md)** | Local copy; authoritative **[OCP PDF](https://www.opencompute.org/documents/datacenter-nvme-ssd-specification-v2-7-final-pdf-1)**                                                                                |
| **[Development](DEVELOPMENT.md)**                                                                            | Style, tests, workflow                                                                                                                                                                                           |
| **[Testing](README_TESTING.md)**                                                                             | Mock data and test commands                                                                                                                                                                                      |
| **[Contributing](CONTRIBUTING.md)**                                                                          | Contributions                                                                                                                                                                                                    |
| **[Technician deployment](docs/TECHNICIAN_DEPLOYMENT.md)**                                                   | `.deb` vs git install, systemd, dashboard, sudoers                                                                                                                                                               |


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
