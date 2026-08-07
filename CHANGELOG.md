# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Selectable grading profiles** (`binary` / `abcdf`): Revert Standard graduated A–F pipeline (age cap, defect bands, recency-weighted self-test, tri-state certification) vs CDI v0.11.0-compatible binary fail-gates. Default `abcdf`; use `--grading-profile binary` for prior behavior. (#115–#121, #125)
- **Revert §13/§15 output fields:** `grading_status` / UNGRADED rows for scan failures, `warning_flags`, `fail_reason_codes`, `attribute_grades`, `age_cap_grade`, and related report schema. (#117, #120, #122)

### Changed
- **Deduction display (#119):** graduated attribute findings show `[grade X]` / `(grade X)` in CLI explain, HTML evidence, and CSV short form instead of cosmetic `[-N]` point values that are not subtracted under `abcdf`. Non-band warnings still show real arithmetic points.
- **Docker:** single `deploy/docker/docker-compose.yml` + `./scripts/docker-up.sh` entry point (prior host/lan-discover/remote-bench overlays removed).

### Fixed
- **Operational state / TUR (#123):** `_check_operational_state` treats TUR `"Not Ready"` as Stage 1 F-NO-RESPONSE (in addition to legacy `"Fail"`). After v0.10.0, `state` is the real TUR result and is never overwritten to `"Fail"` by protocol grading.

## [0.11.0] - 2026-07-20

### Changed
- Report/API surface and dashboard integration updates (see release notes).
- **Operational-state field meaning (continued from 0.10.0):** top-level `state` remains TUR Ready / Not Ready only. The historic `"Device operational state failed"` deduction still existed in scoring but could not fire on live `"Not Ready"` until later wiring (#123). Defect/SMART/temperature fail-gates remain independent critical deductions — removing scan-time `state="Fail"` overwrites eliminated double-counting, not protection.

### Notes
- Technician packaging docs may still cite **0.9.5** for `.deb` / GHCR; treat this tag as the mid-cycle CLI/API line between 0.9.5 and the grading-profile work on `develop`.

## [0.10.0] - 2026-07-18

### Changed
- **Scan engine hardening:** protocol handlers collect metrics only; deleted scan-time assignments that overwrote TUR `state` with `"Fail"` when defects/SMART failed. `state` is now `"Ready"` / `"Not Ready"` from `sg_turs` (or equivalent).
- **Self-test scoring:** ATA/SCSI self-test failures scored like NVMe (critical deduction / Grade F among recent log entries). Recency-weighted §10 bands arrive later in the `abcdf` profile (#121).
- Subprocess timeouts and stricter smartctl open/parse failure handling; failed opens moved to `devices.failures` (reporting of those rows as UNGRADED landed later — #117 / #122).

### Fixed
- Unified grading on `HealthScoreCalculator` (no divergent legacy grade paths).

## [0.9.5] - 2026-06-21

Current technician release: Docker GHCR images, `.deb` packages, and documentation target **0.9.5**.

### Added
- **Docker host-network overlay** (`deploy/docker/docker-compose.host.yml`): API on the host network for Linux LAN discovery; Mac/Linux dashboard on port 3000 via socat sidecar + nginx in the API network namespace.
- **LAN discovery Docker stack** (`docker-compose.lan-discover.yml`, `./scripts/docker-lan-discover.sh`): dashboard + local bridged API without `BENCH_IP`; enter lab subnet on **Discover** (works on macOS Docker Desktop).
- **`./scripts/docker-reset.sh`**: tear down all compose overlays; `--clear-data` removes cached API scans when switching stacks.
- **Team testing guide** (`docs/TEAM_TESTING.md`): end-to-end validation for bench `.deb` + laptop Docker.

### Changed
- **Dashboard mock data:** fixture scans are opt-in via **Use mock data** on **Discover** (localStorage). Live scans are the default.
- **Docker API:** no longer forces mock via image entrypoint or compose env.
- **Remote-bench script:** `BENCH_IP=… ./scripts/docker-remote-bench.sh` pins all API traffic (including scans) to one bench; primary discovery path is `./scripts/docker-lan-discover.sh`.

### Fixed
- **`.deb` on Python 3.14+:** postinst creates `/opt/cdi-health/venv` and pip-installs the bundled wheel with `[api]` extras (Ubuntu 26+ pydantic-core ABI).
- **Docker host overlay on Mac:** localhost dashboard and API proxy via socat; prefer lan-discover for lab subnet probing on Docker Desktop.
- **Compose overlay switching:** reduced race errors (`No such container`) when moving between host, bridged, and remote-bench stacks.

## [0.9.0] - 2026-05-24

Initial public dashboard/API release line. Use **v0.9.5** for technician deployment.

See git history and [v0.9.0 release notes](https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.9.0) for full 0.9.0 detail.

## [1.0.0] - 2025-02-01

### Added
- Initial beta release (pre-dashboard CLI line).

[Unreleased]: https://github.com/circulardrives/cdi-grading-tool/compare/v0.11.0...HEAD
[0.11.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.11.0
[0.10.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.10.0
[0.9.5]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.9.5
[0.9.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.9.0
[1.0.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v1.0.0
