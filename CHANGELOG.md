# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.12.0] - 2026-09-26

### Added
- **Selectable grading profiles** (`binary` / `abcdf`): Revert Standard graduated A–F pipeline (age cap, defect bands, recency-weighted self-test, tri-state certification) vs CDI v0.11.0-compatible binary fail-gates. Default `abcdf`; use `--grading-profile binary` for prior behavior. (#115–#121, #125)
- **Revert §13/§15 output fields:** `grading_status` / UNGRADED rows for scan failures, `warning_flags`, `fail_reason_codes`, `attribute_grades`, `age_cap_grade`, and related report schema. (#117, #120, #122)
- **Available spare grading (#133):** SSD available spare is the primary SSD health signal and is graded A ≥ 80%, B ≥ 60%, C ≥ 40%, D ≥ AVSPT, F < AVSPT (`nvme.available_spare_bands`); SATA SSD attribute 232 uses the same bands.
- **Warning flags:** `TUR_UNAVAILABLE`, `TUR_NOT_READY` (#128), `POH_NOT_REPORTED` (#129), `MISSING_DEFECT_DATA` (#134), `ENDURANCE_EXCEEDED` (#133).
- **API:** `grading_profile` on scan/report requests; `ungraded` count in summaries; HTTP 409 while drive hardware is busy (#131, #136).
- **CI/release:** pytest on Python 3.10/3.12/3.13, `.deb` install smoke test (Ubuntu 22.04, Debian 12), API container smoke test, `SHA256SUMS`, build-provenance attestations and image SBOMs; releases gated on tests (#140).

### Changed
- **Deduction display (#119):** graduated attribute findings show `[grade X]` / `(grade X)` in CLI explain, HTML evidence, and CSV short form instead of cosmetic `[-N]` point values that are not subtracted under `abcdf`. Non-band warnings still show real arithmetic points.
- **Docker:** single `deploy/docker/docker-compose.yml` + `./scripts/docker-up.sh` entry point (prior host/lan-discover/remote-bench overlays removed).
- **SSD wear policy (#133):** percentage used below 100% never changes the letter grade (−5 at 80%, −10 at 90%). At/past rated endurance a drive grades **C** (**D** with any other warning) instead of F under `abcdf`; `nvme.endurance_exceeded_grade: F` restores the fail-gate. `binary` is unchanged.
- **Missing data (#134):** unreported critical defect counters (ATA 5, HDD 197, SCSI grown defects / uncorrected errors, NVMe spare) cap the grade at B instead of reading as 0 / healthy.
- **Thresholds config (#137):** an explicit `--config` / API `config` that is missing, unparseable, or fails schema validation is a hard error (CLI exit 2, HTTP 400).
- **Security (#132, #138):** discovery never sends the bench token unless `probe_token` is given; constant-time token compare; API data paths restricted to an allowlist; narrowed non-root sudoers profile (sudo ≥ 1.9.10); systemd sandboxing; dashboard no longer embeds the API token in the bundle.
- **Packaging (#141):** postinst fails loudly, restarts the API on upgrade; prerm/postrm added; RPM no longer depends on `python3-venv`; example drop-ins ship under `/usr/share/cdi-health/examples/`.
- **Spec:** `docs/CDI_HEALTH_SPEC.md` documents the abcdf pipeline, SSD endurance/spare policy, readiness, missing-data, self-test decoding, warning flags, and tri-state certification.

### Fixed
- **Operational state / TUR (#123):** `_check_operational_state` treats TUR `"Not Ready"` as Stage 1 F-NO-RESPONSE (in addition to legacy `"Fail"`). After v0.10.0, `state` is the real TUR result and is never overwritten to `"Fail"` by protocol grading.
- **TUR false fails (#128):** sg_turs tool errors / missing sg3_utils no longer fail drives (readiness Unknown); genuine Not Ready is retried after START UNIT; ATA/NVMe Not Ready is waived when SMART data is readable. SCSI Not Ready remains F-NO-RESPONSE.
- **Power-on hours (#129):** unknown POH is "Not Reported", never `0`.
- **NVMe self-test (#130):** Log Page 06h decoded per spec (28-byte entries, result/code nibbles); results 5–7 are failures and 1–4/8/9 aborts, in CLI, API, and scoring. `selftest --wait` no longer reports an empty log as a pass.
- **API UNGRADED (#131):** API scans apply the same UNGRADED/Revert fields as the CLI instead of grading those drives F.
- **ATA SSD wear semantics (#135):** Micron/Crucial 202 and Kingston/SandForce 231 are read as life remaining; HGST/Toshiba/WDC vendor detection fixed.
- **API thresholds (#136):** per-request `config` no longer mutates global thresholds.
- **Dashboard (#143, #144):** Revert fields typed and UNGRADED rendered; history pagination and host filter; stable row keys; a11y fixes; reactive selected host.
- **Versions (#139):** API reports the package version; stale 0.9.5 pins removed from docs and build defaults.

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

## Initial beta - 2025-02-01

### Added
- Initial beta release (pre-dashboard CLI line).

[Unreleased]: https://github.com/circulardrives/cdi-grading-tool/compare/v0.12.0...HEAD
[0.12.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.12.0
[0.11.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.11.0
[0.10.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.10.0
[0.9.5]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.9.5
[0.9.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.9.0
