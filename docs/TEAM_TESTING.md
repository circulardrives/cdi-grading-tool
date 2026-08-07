# CDI Health — team testing guide

Use this guide to validate the technician workflow: **Docker dashboard on a laptop** + **`.deb` API on a grading bench** on the lab LAN.

**Images:** GHCR `:latest` (or pin with `CDI_VERSION=<semver>`). See [GitHub Releases](https://github.com/circulardrives/cdi-grading-tool/releases).

---

## Slack / email (copy-paste)

> **CDI Health — please test technician workflow**
>
> **One command on the laptop:** `./scripts/docker-up.sh` → open http://127.0.0.1:3000. Mock fixtures are **off by default**; enable **Use mock data** on Discover for demos.
>
> **Bench (Linux):** install or upgrade the `.deb`, enable the LAN drop-in (`0.0.0.0:8844`) with `CDI_HEALTH_API_TOKEN` set so Discover can find it.
>
> **Laptop (Mac or Linux):**
> 1. `./scripts/docker-up.sh` → Discover → subnet `192.168.0.0/24` → confirm your bench appears.
> 2. For **live drive scans** in the UI: `./scripts/docker-up.sh --bench <bench-ip>` → Scan → expect real serials (not `MOCK…`).
>
> Full steps: [docs/TEAM_TESTING.md](TEAM_TESTING.md) in the repo.

---

## Prerequisites

| Role | Requirement |
| ---- | ----------- |
| **Grading bench** | Debian/Ubuntu, drives attached, ports **8844** reachable from the laptop LAN |
| **Technician laptop** | Docker Desktop (Mac) or Docker Engine (Linux), git clone of `cdi-grading-tool` |
| **Network** | Laptop and bench on same lab LAN (e.g. `192.168.0.0/24`) |

---

## Part A — Grading bench (`.deb`)

On the bench (example: `h12-rome` / `192.168.0.74`):

```bash
# Download latest .deb from GitHub Releases
# https://github.com/circulardrives/cdi-grading-tool/releases/latest
sudo apt update
sudo apt install ./cdi-health_*_all.deb

cdi-health --version
sudo systemctl enable --now cdi-health-api

# Expose API on the lab network (requires token — see lan.conf drop-in)
sudo cp /path/to/cdi-grading-tool/deploy/systemd/cdi-health-api.env.example /etc/default/cdi-health-api
# edit /etc/default/cdi-health-api — set CDI_HEALTH_API_TOKEN
sudo mkdir -p /etc/systemd/system/cdi-health-api.service.d
sudo cp /path/to/cdi-grading-tool/deploy/systemd/cdi-health-api.service.d/lan.conf \
  /etc/systemd/system/cdi-health-api.service.d/lan.conf
sudo systemctl daemon-reload && sudo systemctl restart cdi-health-api

curl -s http://127.0.0.1:8844/api/v1/health
sudo cdi-health scan
```

**Pass criteria:** health JSON `status: ok` (full detail on loopback); scan shows real drive serials and grades. Token is required for LAN binds.

---

## Part B — Laptop Docker (LAN discovery)

From the repo root on the laptop:

```bash
./scripts/docker-up.sh
open http://127.0.0.1:3000   # or visit in browser
```

1. Open **Discover**.
2. Subnet: `192.168.0.0/24` (adjust to your lab).
3. Click **Discover on LAN** / **Start discovery**.

**Pass criteria:** at least one host listed (e.g. `192.168.0.74:8844`). You can add it to **Hosts**.

**Note (v1):** Discover uses the local Docker API; for **Scan** on the remote bench use Part C.

---

## Part C — Live scans through Docker (remote bench)

Pin all dashboard API traffic to one bench:

```bash
./scripts/docker-up.sh --bench 192.168.0.74
open http://127.0.0.1:3000
```

1. **Scan** or **Drive Health** → run a scan.
2. Confirm **real serial numbers** (e.g. `50PY102AYZ5L`) — not `MOCK000000`.
3. Optional: compare with direct bench API:

```bash
curl -s -X POST http://192.168.0.74:8844/api/v1/scan \
  -H 'Content-Type: application/json' \
  -H "X-API-Token: $CDI_HEALTH_API_TOKEN" \
  -d '{}'
```

**Pass criteria:** device count and serials match between Docker UI and direct bench curl.

---

## Part D — Mock demo (opt-in)

Mock is **not** the default. To test fixtures:

```bash
./scripts/docker-up.sh
open http://127.0.0.1:3000
```

1. **Discover** → **Demo mode** → enable **Use mock data**.
2. **Scan** → expect fixture devices.

Or without the UI toggle (API-only mock):

```bash
curl -s -X POST http://127.0.0.1:3000/api/cdi/api/v1/scan \
  -H 'Content-Type: application/json' \
  -d '{"mock_data":"/app/src/cdi_health/mock_data"}'
```

---

## Quick reference

| Goal | Command |
| ---- | ------- |
| Start / update stack | `./scripts/docker-up.sh` |
| Live scans on one bench | `./scripts/docker-up.sh --bench <ip>` |
| Build from source | `./scripts/docker-up.sh --build` |
| Mock fixtures | `./scripts/docker-up.sh` → Discover → **Use mock data** |
| Stop / reset | `./scripts/docker-up.sh down` / `./scripts/docker-up.sh reset` |

See also [Technician deployment](TECHNICIAN_DEPLOYMENT.md).

---

## Report issues

File bugs against [circulardrives/cdi-grading-tool](https://github.com/circulardrives/cdi-grading-tool/issues) with: OS, Docker version, bench IP, health JSON, and whether mock was enabled.
