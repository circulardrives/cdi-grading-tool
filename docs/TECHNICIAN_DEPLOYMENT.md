# Technician Deployment Guide

This guide covers two common setups:

1. **`.deb` package** — fastest way to get `cdi-health` and `cdi-health-api` on Debian/Ubuntu (see [GitHub Releases](https://github.com/circulardrives/cdi-grading-tool/releases)). Does **not** include the web dashboard.
2. **Git clone + Python venv** — use when you need the **technician dashboard** (Vite + bun monorepo in `dashboard/`) or a matching editable API install.

Both expect **Linux** with access to storage tooling (see below).

## Required tools (real hardware)

Install before scanning **live** drives (not needed for `--mock-data` workflows):

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

## Option A — Install from `.deb`

The package declares **Depends** on `python3`, `smartmontools`, and `nvme-cli`, and **Recommends** `openseachest` (OpenSeaChest). Prefer apt so dependencies install in one step:

```bash
sudo apt update
sudo apt install ./cdi-health_*_all.deb
cdi-health --version
sudo cdi-health scan
```

On **Ubuntu 24.04+** and **Debian Trixie+**, `openseachest` is pulled from apt automatically (Ubuntu: enable **universe**). On **Ubuntu 22.04** or **Debian Bookworm**, run `sudo ./scripts/install-host-dependencies.sh` first if OpenSeaChest is not in your apt sources.

For SAS/SCSI: `sudo apt install sg3-utils` (also suggested by the package).

Layout:

- **`/usr/local/bin/cdi-health`** — CLI
- **`/usr/local/bin/cdi-health-api`** — API entry point
- **`/opt/cdi-health/lib`** — application Python tree

Systemd unit **`cdi-health-api.service`** may be installed under `/usr/lib/systemd/system/`; enable it if you want the API on boot (see below).

For **dashboard + API** together, pair this CLI/API install with a **separate** dashboard build (Option B dashboard steps), run `./scripts/start-local-mock.sh` from a dev clone, or run API only and point a workstation UI at the host’s `:8844` endpoint.

---

## Option B — Install backend from git (venv)

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
# Set VITE_CDI_API_PROXY_TARGET to your API (e.g. http://127.0.0.1:8844)
# and VITE_CDI_USE_MOCK_DATA=0 for live scans before building.
bun install
bun run build
```

Local dev without systemd: `bun run dev` → http://127.0.0.1:3000. All-in-one mock from repo root: `./scripts/start-local-mock.sh`.

## Install systemd Services

Paths assume the repo lives at `/opt/cdi-grading-tool` (adjust `cp` sources if you cloned elsewhere).

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
curl -s http://127.0.0.1:8844/api/v1/health
curl -s http://127.0.0.1:3000
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

- Keep API bound to `127.0.0.1`.
- Use `CDI_HEALTH_API_TOKEN` if dashboard/API run as separate users.
- Do not expose either service directly to untrusted networks.
