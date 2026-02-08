# CDI Dashboard Backend Architecture

## Runtime Model

- Backend runs locally on the same host that has attached drives.
- Backend binds to `127.0.0.1` by default and is not intended for public hosting.
- Backend process runs as root for real device access (`smartctl`, `nvme`, `sg3-utils`).
- Optional static token auth can be enabled with `CDI_HEALTH_API_TOKEN` (or `--api-token`).

## Components

- `cdi_health.api.app`: FastAPI app and HTTP routes.
- `cdi_health.api.services`: Scan, self-test, and report service layer.
- `cdi_health.api.jobs`: In-memory async job tracking for long-running actions.
- `cdi_health.api.security`: Root enforcement and optional token validation.

## HTTP Endpoints

- `GET /api/v1/health`
- `POST /api/v1/scan`
- `GET /api/v1/devices`
- `POST /api/v1/selftests`
- `GET /api/v1/selftests/status`
- `POST /api/v1/selftests/abort`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/reports`

## Run Locally

```bash
pip install -e .[api]
sudo cdi-health-api --host 127.0.0.1 --port 8844
```

Development mode without root (mock/testing only):

```bash
cdi-health-api --allow-non-root
```

## Optional systemd Unit

```ini
[Unit]
Description=CDI Health Local API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/cdi-grading-tool
ExecStart=/usr/local/bin/cdi-health-api --host 127.0.0.1 --port 8844
Restart=on-failure
Environment=CDI_HEALTH_API_TOKEN=replace-me

[Install]
WantedBy=multi-user.target
```
