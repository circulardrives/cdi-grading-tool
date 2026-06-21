# CDI Health 0.9.5 — team testing guide

Use this guide to validate the technician workflow: **Docker dashboard on a laptop** + **`.deb` API on a grading bench** on the lab LAN.

**Release:** [v0.9.5](https://github.com/circulardrives/cdi-grading-tool/releases/tag/v0.9.5)

---

## Slack / email (copy-paste)

> **CDI Health 0.9.5 — please test technician workflow**
>
> We consolidated on **0.9.5** for Docker images, `.deb` packages, and docs. Mock fixture data is **off by default**; enable **Use mock data** on the **Discover** page only for demos.
>
> **Bench (Linux):** install or upgrade the `.deb`, enable `cdi-health-api` on `0.0.0.0:8844` so Discover can find it.
>
> **Laptop (Mac or Linux):**
> 1. `./scripts/docker-lan-discover.sh` → Discover → subnet `192.168.0.0/24` → confirm your bench appears.
> 2. For **live drive scans** in the UI: `BENCH_IP=<bench-ip> ./scripts/docker-remote-bench.sh` → Scan → expect real serials (not `MOCK…`).
>
> If compose fails when switching stacks: `./scripts/docker-reset.sh --clear-data`
>
> Full steps: [docs/TEAM_TESTING.md](TEAM_TESTING.md) in the repo.

---

## Prerequisites

| Role | Requirement |
| ---- | ----------- |
| **Grading bench** | Debian/Ubuntu, drives attached, ports **8844** reachable from the laptop LAN |
| **Technician laptop** | Docker Desktop (Mac) or Docker Engine (Linux), git clone of `cdi-grading-tool` on branch `fix/deb-py314-and-remote-bench` or `main` after merge |
| **Network** | Laptop and bench on same lab LAN (e.g. `192.168.0.0/24`) |

---

## Part A — Grading bench (`.deb`)

On the bench (example: `h12-rome` / `192.168.0.74`):

```bash
# Download from GitHub Releases (v0.9.5)
wget https://github.com/circulardrives/cdi-grading-tool/releases/download/v0.9.5/cdi-health_0.9.5_all.deb
sudo apt update
sudo apt install ./cdi-health_0.9.5_all.deb

cdi-health --version
sudo systemctl enable --now cdi-health-api

# Expose API on the lab network (required for Discover from a laptop)
sudo mkdir -p /etc/systemd/system/cdi-health-api.service.d
printf '[Service]\nExecStart=\nExecStart=/usr/local/bin/cdi-health-api --host 0.0.0.0 --port 8844 --data-dir /var/lib/cdi-health\n' | sudo tee /etc/systemd/system/cdi-health-api.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart cdi-health-api

curl -s http://127.0.0.1:8844/api/v1/health
sudo cdi-health scan
```

**Pass criteria:** health JSON `status: ok`; scan shows real drive serials and grades.

**Python 3.14+ (Ubuntu 26):** postinst creates `/opt/cdi-health/venv` automatically. If API fails on pydantic, reinstall the 0.9.5 `.deb` from PR #63 build.

---

## Part B — Laptop Docker (LAN discovery)

From the repo root on the laptop:

```bash
./scripts/docker-reset.sh --clear-data
CDI_VERSION=0.9.5 ./scripts/docker-lan-discover.sh
open http://127.0.0.1:3000   # or visit in browser
```

1. Open **Discover**.
2. Subnet: `192.168.0.0/24` (adjust to your lab).
3. Click **Discover on LAN** / **Start discovery**.

**Pass criteria:** at least one host listed (e.g. `192.168.0.74:8844`). You can add it to **Hosts**.

**Note (v1):** Discover uses the local Docker API; **Scan** on this stack does not run on the remote bench yet.

---

## Part C — Live scans through Docker (remote bench)

Pin all dashboard API traffic to one bench:

```bash
./scripts/docker-reset.sh
BENCH_IP=192.168.0.74 ./scripts/docker-remote-bench.sh
open http://127.0.0.1:3000
```

1. **Scan** or **Drive Health** → run a scan.
2. Confirm **real serial numbers** (e.g. `50PY102AYZ5L`) — not `MOCK000000`.
3. Optional: compare with direct bench API:

```bash
curl -s -X POST http://192.168.0.74:8844/api/v1/scan -H 'Content-Type: application/json' -d '{}'
```

**Pass criteria:** device count and serials match between Docker UI and direct bench curl.

---

## Part D — Mock demo (opt-in)

Mock is **not** the default. To test fixtures:

```bash
./scripts/docker-reset.sh --clear-data
docker compose -f deploy/docker/docker-compose.yml up -d --build
open http://127.0.0.1:3000
```

1. **Discover** → **Demo mode** → enable **Use mock data**.
2. **Scan** → expect ~22 fixture devices.

Or without rebuilding the dashboard (API-only mock):

```bash
curl -s -X POST http://127.0.0.1:3000/api/cdi/api/v1/scan \
  -H 'Content-Type: application/json' \
  -d '{"mock_data":"/app/src/cdi_health/mock_data"}'
```

---

## Part E — Switching stacks (cleanup)

When changing between lan-discover, remote-bench, mock demo, or host overlay:

```bash
./scripts/docker-reset.sh --clear-data
```

Then start the stack you need (see [Technician deployment](TECHNICIAN_DEPLOYMENT.md)).

---

## Quick reference

| Goal | Command |
| ---- | ------- |
| Find benches on LAN | `CDI_VERSION=0.9.5 ./scripts/docker-lan-discover.sh` |
| Live scans on one bench | `BENCH_IP=<ip> ./scripts/docker-remote-bench.sh` |
| Mock fixtures (UI toggle) | `docker compose -f deploy/docker/docker-compose.yml up -d --build` → Discover → **Use mock data** |
| Reset / fix compose errors | `./scripts/docker-reset.sh --clear-data` |

---

## Report issues

Include: stack command used, `curl http://127.0.0.1:3000/api/cdi/api/v1/health`, bench IP, and whether serials look like `MOCK…` or real hardware.

Open a GitHub issue or reply in the team channel with **pass/fail** for parts A–D.
