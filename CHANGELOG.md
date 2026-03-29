# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- Improved terminal output formatting for better readability on any console size
- Self-test command now detects and displays existing test results instead of always starting new tests
- Enhanced error handling for self-test operations

### Technical Details
- Self-test implementation follows NVMe Base Specification 2.3
- Uses `nvme-cli` for self-test operations
- Checks OACS bit 4 (Device Self-Test supported) via `nvme id-ctrl`

### Features
- **Scan Command**: Comprehensive device health scanning with detailed table output
- **Report Command**: Generate detailed HTML or PDF health reports
- **Watch Command**: Continuous monitoring of device health with configurable intervals
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

## [0.8] - 2026-03-29

### Added
- Mock SMART/NVMe export path for reproducible reports and tests (`mock_export`, expanded mock fixtures).
- FastAPI health smoke test coverage and `httpx` dev dependency for `TestClient`.
- HDD sector scoring thresholds and NVMe advanced reporting fields in HTML/PDF output.

### Changed
- Consolidated GitHub Actions CI (build, pre-commit, pytest matrix with OS tools, dashboard `next build`, wheel smoke, license headers).
- Technician dashboard: React 19-compatible component types, drive-health and reporting UX updates.

## [1.0.0] - 2025-02-01

### Added
- Initial beta release
- Core scanning functionality
- Health assessment algorithms
- Report generation
- Watch/monitoring mode

[Unreleased]: https://github.com/circulardrives/cdi-grading-tool/compare/v0.8...HEAD
[0.8]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.8
[1.0.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v1.0.0
