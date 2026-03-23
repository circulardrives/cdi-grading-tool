# Technician Deployment Guide

This guide sets up CDI for local technician use with:

- `cdi-health-api` (root-local API on `127.0.0.1:8844`)
- Next.js dashboard (local UI on `127.0.0.1:3000`)

## 1. Install Backend

The deb package installs the backend library under `/opt/cdi-health/lib` and
the CLI/API entrypoints under `/usr/local/bin`, so no extra Python install step
is required.

Ensure required device tools are installed:

```bash
sudo apt install smartmontools nvme-cli sg3-utils
```

## 2. Install Dashboard

```bash
cd /opt/cdi-health/dashboard
cp .env.example .env.local
npm install
npm run build
```

## 3. Install systemd Services

```bash
sudo cp /opt/cdi-health/deploy/systemd/cdi-health-api.service /etc/systemd/system/
sudo cp /opt/cdi-health/deploy/systemd/cdi-health-dashboard.service /etc/systemd/system/
```

Optional env files:

```bash
sudo cp /opt/cdi-health/deploy/systemd/cdi-health-api.env.example /etc/default/cdi-health-api
sudo cp /opt/cdi-health/deploy/systemd/cdi-health-dashboard.env.example /etc/default/cdi-health-dashboard
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cdi-health-api.service
sudo systemctl enable --now cdi-health-dashboard.service
```

## 4. Verify

```bash
curl -s http://127.0.0.1:8844/api/v1/health
curl -s http://127.0.0.1:3000
```

## 5. Optional Sudoers Profile (Non-Root API)

Preferred model: run `cdi-health-api` as root via systemd.

If you must run API as non-root service account, install the optional policy:

```bash
sudo cp /opt/cdi-health/deploy/sudoers/cdi-health-technician /etc/sudoers.d/cdi-health-technician
sudo chmod 440 /etc/sudoers.d/cdi-health-technician
sudo visudo -cf /etc/sudoers.d/cdi-health-technician
```

Then edit the file and replace `cdiapi` with your service account.

## Security Notes

- Keep API bound to `127.0.0.1`.
- Use `CDI_HEALTH_API_TOKEN` if dashboard/API run as separate users.
- Do not expose either service directly to untrusted networks.
