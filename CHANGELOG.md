# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Docker Compose** stack under `deploy/docker/` for API + dashboard without local Python/bun/systemd setup (mock demo by default; optional hardware overlay for live drive scanning).
- `./scripts/docker-up.sh` helper for `docker compose up`.
- **Release workflow** publishes multi-arch Docker images to GHCR on each `v*` tag (`cdi-health-api`, `cdi-health-dashboard`); use `deploy/docker/docker-compose.ghcr.yml` to run published images.

## [0.9.0] - 2026-05-24

### Added
- **Dashboard**: Technician console rebuilt as a Vite + React monorepo (Turborepo/bun) with shadcn/ui, replacing the Next.js app.
- **Dashboard navigation**: Fleet Status, **Hosts**, **Discover**, **Scan**, Drive Health, Health Reports, and NVMe Self-Test as separate pages (replaces the combined Machines view).
- **Machines API**: REST endpoints to register grading hosts and track reachability and scan status.
- **LAN Discovery API**: `GET`/`POST /api/v1/discover` scans private IPv4 subnets for listening CDI Health APIs (TCP probe + health check, rate-limited).
- **Self-test log API**: `GET /api/v1/selftests/status` returns NVMe Log Page 0x06 entries (`recent_results`, progress, completion) alongside live status.
- **Self-test dashboard UI**: Expanded NVMe Self-Test page with log history, progress, and pass/fail details.
- **h12-rome mock fixtures**: Real-world bad-drive scan and SMART fixtures for API/dashboard testing.

- **NVMe Self-Test Support**: New `selftest` command for running and monitoring NVMe device self-tests
  - Automatically detects devices that support self-test
  - Runs short tests by default (completes in ~2 minutes)
  - Extended test support (may take several hours)
  - Displays results in formatted table
  - Shows existing test results on subsequent runs instead of starting new tests
  - Status checking and abort functionality
- **Responsive Terminal Output**: Table formatting adapts to console width
  - Compact layout for narrow terminals (< 100 columns)
  - Full layout with all columns for wide terminals
  - Header box adjusts to terminal size
- **Failed Self-Test Detection**: Failed NVMe self-tests automatically result in Grade F (critical failure)
  - Integrated into health scoring system
  - Prevents certification of drives with failed self-tests

### Changed
- Debian/RPM packages declare `smartmontools` and `nvme-cli` as dependencies, recommend openSeaChest, and run a post-install helper for host tooling.
- CI builds the dashboard with bun and Turborepo.
- README, DEVELOPMENT.md, DASHBOARD_API.md, and TECHNICIAN_DEPLOYMENT.md updated for the Vite dashboard, LAN discovery, and remote-host dev workflow.
- systemd dashboard unit (`cdi-health-dashboard.service`) runs `bun run start` instead of npm.

- Improved terminal output formatting for better readability on any console size
- Self-test command now detects and displays existing test results instead of always starting new tests
- Enhanced error handling for self-test operations
- Tightened CDI health scoring so critical health deductions are hard fail-gates that produce Grade F / score 0.
- NVMe health scoring now uses the drive-reported available-spare threshold when present, treats non-zero critical warnings and media/data-integrity errors as failures, and parses smartctl `table[].self_test_result.value` self-test failures.
- SCSI/SAS scoring now recognizes parser output stored as `offline_uncorrectable_sectors` for combined uncorrected read/write/verify errors.
- Power-on hours remain report telemetry and no longer create score deductions for missing NVMe self-test history.
- HTML/CSV reports now surface SCSI/SAS non-medium errors as telemetry for trend review.
- Reorganized the health specification into drive-class sections for SATA HDD, SAS HDD, SATA SSD, SAS SSD, and NVMe SSD.
- Added openSeaChest health-check workflow notes to clarify SMART warnings, unavailable SMART checks, DST failure modes, Device Statistics preference, and telemetry-only counters.
- Updated the README health summary to point to the main-repo CDI health spec and mirror the drive-class grading model.
- Fixed release packaging so `.deb` and `.rpm` package versions come from the pushed git tag.
- Accounted for nFPM's normalized SemVer package filenames, e.g. tag `v0.9` produces OS packages named `0.9.0`.

### Removed
- **Watch command**: Continuous monitoring mode removed from CLI and examples (use periodic `scan`/`report` or the REST API instead).

### Technical Details
- Self-test implementation follows NVMe Base Specification 2.3
- Uses `nvme-cli` for self-test operations
- Checks OACS bit 4 (Device Self-Test supported) via `nvme id-ctrl`

### Features
- **Scan Command**: Comprehensive device health scanning with detailed table output
- **Report Command**: Generate detailed HTML or PDF health reports
- **Self-Test Command**: Run and monitor NVMe device self-tests
- **Multiple Output Formats**: Table (default), JSON, CSV, YAML
- **Health Scoring**: 0-100 score with letter grades (A-F)
- **Protocol Support**: ATA/SATA, NVMe, SCSI/SAS devices
- **Mock Mode**: Test functionality without physical devices

### Technical Details
- Python 3.10+ support
- Requires: nvme-cli, smartmontools (sg3-utils optional)
- Proper CLI entry point: `cdi-health` command
- Package can be installed via pip: `pip install cdi-health`
- Version managed via setuptools-scm from git tags

## [1.0.0] - 2025-02-01

### Added
- Initial beta release
- Core scanning functionality
- Health assessment algorithms
- Report generation
- Watch/monitoring mode

[Unreleased]: https://github.com/circulardrives/cdi-grading-tool/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/circulardrives/cdi-grading-tool/compare/v0.8...v0.9.0
[1.0.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v1.0.0
