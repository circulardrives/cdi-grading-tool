# Technician Deployment Guide

Docker stacks below always pull **`latest`** from GHCR (published on each [GitHub release](https://github.com/circulardrives/cdi-grading-tool/releases)). Pin a semver tag only when you need a fixed build.

Team end-to-end test plan: **[TEAM_TESTING.md](TEAM_TESTING.md)**.

This guide covers three common setups:

1. **Docker Compose** — run the **dashboard + API** on a technician laptop without Python, bun, or systemd.
2. **`.deb` package** — install `cdi-health` and `cdi-health-api` on Debian/Ubuntu grading benches (no web UI in the package).
3. **Git clone + Python venv** — editable install, custom patches, or production systemd on bare metal.

Bare-metal grading hosts expect **Linux** with storage tooling (see below).

## Option A — Docker Compose

Requires [Docker](https://docs.docker.com/get-docker/) with Compose v2.

**Reset when switching stacks:**

```bash
./scripts/docker-reset.sh --clear-data
```

### Prerequisites

1. Clone the repo (Compose files and helper scripts live here; images come from GHCR):

```bash
git clone https://github.com/circulardrives/cdi-grading-tool.git
cd cdi-grading-tool
```

2. Copy env and set a token:

```bash
cp deploy/docker/.env.example deploy/docker/.env
# edit deploy/docker/.env — set CDI_HEALTH_API_TOKEN to a strong random value
# optional: DASHBOARD_PORT (default 3000)
```

Compose fails fast if the token is missing; nginx injects `X-API-Token` for `/api/cdi` (the SPA must not embed the token).

**Auth:** images are public on GHCR — no `docker login` required for pulls.

Images (`linux/amd64`, `linux/arm64`):

- `ghcr.io/circulardrives/cdi-health-api:latest`
- `ghcr.io/circulardrives/cdi-health-dashboard:latest`

(`:latest` is updated on every tagged release. Override with `CDI_VERSION=<semver>` only to pin.)

### Default stack (always pull latest)

```bash
# Prefer an explicit latest tag so helper scripts do not fall back to an old default
export CDI_VERSION=latest

docker compose -f deploy/docker/docker-compose.ghcr.yml pull
docker compose -f deploy/docker/docker-compose.ghcr.yml up -d
```

`deploy/docker/docker-compose.ghcr.yml` defaults to `:latest` and sets `pull_policy: always` (Compose v2). Re-running `up -d` after a new release still refreshes images; using `pull` first makes the update explicit.

Open http://127.0.0.1:3000 — **live scans default**; enable **Use mock data** on **Discover** for fixtures.

### Verify version

On the default GHCR stack the API is not published on the host — use the dashboard proxy or `exec`:

```bash
# Via nginx on the dashboard port (default 3000)
curl -s http://127.0.0.1:3000/api/cdi/api/v1/health
# → {"status":"ok","version":"..."}

# Or inside the API container
docker exec cdi-health-api \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8844/api/v1/health').read().decode())"

# Confirm which GHCR digests you are running
docker compose -f deploy/docker/docker-compose.ghcr.yml images
docker image inspect ghcr.io/circulardrives/cdi-health-api:latest \
  --format '{{.RepoDigests}} {{.Created}}'
```

With the Linux host-network overlay, `curl -s http://127.0.0.1:8844/api/v1/health` works directly.

### Update (re-pull latest)

```bash
export CDI_VERSION=latest
docker compose -f deploy/docker/docker-compose.ghcr.yml pull
docker compose -f deploy/docker/docker-compose.ghcr.yml up -d
```

Same pattern for LAN / host / remote-bench helpers: set `CDI_VERSION=latest`, then re-run the script (or `pull` + `up`).

### LAN discovery (find remote grading benches)

**macOS and Linux (recommended):** local API on the default Docker bridge. Enter your lab subnet on the **Discover** page — no `BENCH_IP` required.

```bash
CDI_VERSION=latest ./scripts/docker-lan-discover.sh
```

Open http://127.0.0.1:3000 → **Discover** → subnet `192.168.0.0/24` (or your lab CIDR). On macOS Docker Desktop, host networking uses the VM subnet (~192.168.65.x), but probing an **explicit** lab subnet from the bridged API container reaches benches on your LAN.

**Linux (optional):** host-network overlay auto-detects the local subnet. Port **8844** must be free on your machine.

```bash
CDI_VERSION=latest docker compose \
  -f deploy/docker/docker-compose.ghcr.yml \
  -f deploy/docker/docker-compose.host.yml pull
CDI_VERSION=latest docker compose \
  -f deploy/docker/docker-compose.ghcr.yml \
  -f deploy/docker/docker-compose.host.yml up -d
```

**Pin all API traffic to one bench** (including live scans on that host — not just discovery):

```bash
CDI_VERSION=latest BENCH_IP=192.168.0.74 ./scripts/docker-remote-bench.sh
```

v1 limitation: with `./scripts/docker-lan-discover.sh`, **Discover** finds remote benches, but **Scan** / **Drive Health** still hit the local API container until you select a connected host or use remote-bench mode.

Stop:

```bash
./scripts/docker-reset.sh
# or
./scripts/docker-lan-discover.sh down
```

**Build locally** (optional): `./scripts/docker-up.sh --build` or `./scripts/docker-up.sh --host --build`

For live drive scanning on the bench itself, use Option B (`.deb`) below.

---

## Required tools (bare metal, real hardware)

Install before scanning **live** drives on the host (not needed for Docker mock mode or `--mock-data` workflows):

```bash
sudo apt install smartmontools nvme-cli
sudo apt install sg3-utils   # SCSI/SAS
```

Then verify discovery:

```bash
cdi-health scan
```

Use `sudo cdi-health scan` if your user cannot read SMART / NVMe log pages on the devices.

---

## Option B — Install from `.deb`

Download the newest `cdi-health_*_all.deb` from [GitHub Releases](https://github.com/circulardrives/cdi-grading-tool/releases/latest) (asset name includes the version). The package declares **Depends** on `python3`, `smartmontools`, and `nvme-cli`, and **Recommends** `openseachest` (OpenSeaChest). Prefer apt so dependencies install in one step:

```bash
# After downloading the .deb from the latest release into the current directory:
sudo apt update
sudo apt install ./cdi-health_*_all.deb
cdi-health --version
sudo cdi-health scan
```

On **Ubuntu 24.04+** and **Debian Trixie+**, `openseachest` is pulled from apt automatically (Ubuntu: enable **universe**). On **Ubuntu 22.04** or **Debian Bookworm**, run `sudo ./scripts/install-host-dependencies.sh` first if OpenSeaChest is not in your apt sources.

For SAS/SCSI: `sudo apt install sg3-utils` (also suggested by the package).

Layout:

- **`/usr/local/bin/cdi-health`** — CLI
- **`/usr/local/bin/cdi-health-api`** — API entry point (includes FastAPI/uvicorn dependencies)
- **`/opt/cdi-health/venv`** — Python venv created at install time (matches system `python3`, including 3.14+)
- **`/opt/cdi-health/pkg`** — bundled wheel used by postinst

Systemd unit **`cdi-health-api.service`** may be installed under `/usr/lib/systemd/system/`; enable it if you want the API on boot (see below). It stores state in **`/var/lib/cdi-health`** and does not require a git clone.

**LAN discovery:** the default unit binds to `127.0.0.1` only. For a bench to appear in **Discover** from a technician laptop, use the shipped LAN drop-in (requires a token in `/etc/default/cdi-health-api`):

```bash
sudo cp /opt/cdi-grading-tool/deploy/systemd/cdi-health-api.env.example /etc/default/cdi-health-api
# edit /etc/default/cdi-health-api — set CDI_HEALTH_API_TOKEN to a strong random value
sudo mkdir -p /etc/systemd/system/cdi-health-api.service.d
sudo cp /opt/cdi-grading-tool/deploy/systemd/cdi-health-api.service.d/lan.conf \
  /etc/systemd/system/cdi-health-api.service.d/lan.conf
sudo systemctl daemon-reload && sudo systemctl restart cdi-health-api
```

The API refuses non-loopback binds without `CDI_HEALTH_API_TOKEN`. Trusted lab networks only.

For **fixture demos** on a laptop, use **Option A** with the GHCR stack above (or `docker compose -f deploy/docker/docker-compose.yml up -d --build` from a dev clone) and enable **Use mock data** on Discover, or `./scripts/start-local-mock.sh`.

---

## Option C — Install backend from git (venv)

If `python3 -m venv .venv` fails with **ensurepip** / “python3-venv” errors on Ubuntu, install the matching venv package, for example:

```bash
sudo apt install python3-venv
# or, on some releases: sudo apt install python3.12-venv
```

Then:

```bash
cd /opt/cdi-grading-tool   # or your clone path
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[api]
```

Ensure **smartmontools**, **nvme-cli**, and (if needed) **sg3-utils** are installed as in the first section.

## Install Dashboard (from git tree)

Requires [bun](https://bun.sh) on the machine serving the UI.

```bash
cd /opt/cdi-grading-tool/dashboard
cp apps/web/.env.example apps/web/.env.local
# Set VITE_CDI_API_PROXY_TARGET to your API (e.g. http://127.0.0.1:8844).
# Live scans are the default; enable **Use mock data** on the Discover page for demos.
bun install
bun run build
```

Local dev without systemd: `bun run dev` → http://127.0.0.1:3000. All-in-one mock from repo root: `./scripts/start-local-mock.sh`.

## Install systemd Services

Paths assume the repo lives at `/opt/cdi-grading-tool` (adjust `WorkingDirectory` in the unit files if you cloned elsewhere).

**Dashboard unit prerequisites** (not created automatically):

```bash
# System account for the dashboard service
sudo useradd --system --home /opt/cdi-grading-tool --shell /usr/sbin/nologin cdi
sudo chown -R cdi:cdi /opt/cdi-grading-tool/dashboard

# bun (required by cdi-health-dashboard.service; npm is not supported)
curl -fsSL https://bun.sh/install | bash
# ensure /usr/local/bin/bun exists, or symlink: sudo ln -sf ~/.bun/bin/bun /usr/local/bin/bun

# Production assets (required before `bun run start` / systemd)
cd /opt/cdi-grading-tool/dashboard
sudo -u cdi bun install
sudo -u cdi bun run build
```

**`.deb`-only API install:** the API unit shipped in the package does not need a git clone. It uses `/var/lib/cdi-health` for state and `/opt/cdi-health/lib` for Python. Skip copying the dashboard unit unless you also deployed the dashboard from git.

```bash
sudo cp /opt/cdi-grading-tool/deploy/systemd/cdi-health-api.service /etc/systemd/system/
sudo cp /opt/cdi-grading-tool/deploy/systemd/cdi-health-dashboard.service /etc/systemd/system/
```

Optional env files:

```bash
sudo cp /opt/cdi-grading-tool/deploy/systemd/cdi-health-api.env.example /etc/default/cdi-health-api
sudo cp /opt/cdi-grading-tool/deploy/systemd/cdi-health-dashboard.env.example /etc/default/cdi-health-dashboard
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cdi-health-api.service
sudo systemctl enable --now cdi-health-dashboard.service
```

## Verify

```bash
# Docker default stack (API via nginx proxy):
curl -s http://127.0.0.1:3000/api/cdi/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000

# Bare metal / host-network API:
curl -s http://127.0.0.1:8844/api/v1/health
```

## Optional Sudoers Profile (Non-Root API)

Preferred model: run `cdi-health-api` as root via systemd.

If you must run API as non-root service account, install the optional policy:

```bash
sudo cp /opt/cdi-grading-tool/deploy/sudoers/cdi-health-technician /etc/sudoers.d/cdi-health-technician
sudo chmod 440 /etc/sudoers.d/cdi-health-technician
sudo visudo -cf /etc/sudoers.d/cdi-health-technician
```

Then edit the file and replace `cdiapi` with your service account.

## Security Notes

- Keep API bound to `127.0.0.1` unless you intentionally enable the LAN drop-in.
- `CDI_HEALTH_API_TOKEN` is **mandatory** for any non-loopback bind (`0.0.0.0`, host network, LAN IP). The process exits at startup if the token is missing.
- Prefer terminating auth at nginx: inject `X-API-Token` from a server-only env var; never bake the token into the dashboard JS bundle.
- Do not expose either service directly to untrusted networks.

## Troubleshooting

### `cdi-health-api: Missing API dependencies`

The `.deb` postinst creates **`/opt/cdi-health/venv`** and installs the bundled wheel with `[api]` extras for the system `python3`. Requires **`python3-venv`**. If the API still fails, reinstall the package or run:

```bash
sudo apt install python3-venv
sudo apt install --reinstall ./cdi-health_*_all.deb
```

### `cdi-health-api.service: Changing to the requested working directory failed`

Usually means the unit still points at `/opt/cdi-grading-tool`, which does not exist on `.deb`-only installs. Use the current unit (state under `/var/lib/cdi-health`) or remove/edit `WorkingDirectory` in your copy under `/etc/systemd/system/`, then `sudo systemctl daemon-reload`.

### `cdi-health-dashboard.service: Failed at step USER` / `No such process`

The `cdi` system user must exist before enabling the dashboard unit (see prerequisites above). The service also expects **bun** at `/usr/bin/bun` or on `PATH` for the `cdi` user — not npm. If your unit references `/usr/bin/npm`, replace it with the current `deploy/systemd/cdi-health-dashboard.service` (`ExecStart=/usr/bin/bun run start`).

### Dashboard `ECONNREFUSED 127.0.0.1:8844`

The UI proxy targets the local API. Start the API first and confirm:

```bash
curl -s http://127.0.0.1:8844/api/v1/health
sudo systemctl status cdi-health-api.service   # if using systemd
```

For git + venv: `source .venv/bin/activate && sudo -E cdi-health-api --host 127.0.0.1 --port 8844 --data-dir ./.cdi-health` (venv must have `pip install -e .[api]`).
