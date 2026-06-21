# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/circulardrives/cdi-grading-tool/compare/v0.9.5...HEAD
[0.9.5]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.9.5
[0.9.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.9.0
[1.0.0]: https://github.com/circulardrives/cdi-grading-tool/releases/tag/v1.0.0
