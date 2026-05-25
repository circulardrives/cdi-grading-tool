# CDI Dashboard Backend Architecture

## Runtime Model

- Backend runs locally on the same host that has attached drives.
- Backend binds to `127.0.0.1` by default and is not intended for public hosting.
- Backend process runs as root for real device access (`smartctl`, `nvme`, `sg3-utils`).
- Optional static token auth can be enabled with `CDI_HEALTH_API_TOKEN` (or `--api-token`).
- Host registry and per-host scan snapshots persist under a configurable data directory (default: `./.cdi-health`, env `CDI_HEALTH_DATA_DIR`, or `--data-dir`).

## Components

- `cdi_health.api.app`: FastAPI app and HTTP routes.
- `cdi_health.api.services`: Scan, self-test, and report service layer.
- `cdi_health.api.machines`: JSON-backed fleet host registry and scan association.
- `cdi_health.api.jobs`: In-memory async job tracking for long-running actions.
- `cdi_health.api.security`: Root enforcement and optional token validation.

## HTTP Endpoints

- `GET /api/v1/health`
- `POST /api/v1/scan` — optional `machine_id` associates the scan with a registered host
- `GET /api/v1/devices` — optional `machine_id` returns cached scan for that host; `refresh=true` rescans
- `GET /api/v1/machines` — list registered grading hosts
- `POST /api/v1/machines` — register a host
- `GET /api/v1/machines/{id}` — host detail
- `PATCH /api/v1/machines/{id}` — update host metadata
- `DELETE /api/v1/machines/{id}` — remove host and cached scan snapshot
- `POST /api/v1/selftests`
- `GET /api/v1/selftests/status`
- `POST /api/v1/selftests/abort`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/reports`
- `GET /api/v1/reports/{filename}`

## Host Registry Model

Each machine (host) record includes:

| Field | Description |
| ----- | ----------- |
| `id` | UUID primary key |
| `name` | Display name (required) |
| `hostname` | Host identifier (required) |
| `address` | Optional IP or `host:port` for a future remote CDI API agent |
| `location` | Optional rack / data-center label |
| `notes` | Optional technician notes |
| `status` | `unknown`, `reachable`, or `unreachable` |
| `last_seen_at` | Last time the host was observed (updated on successful scan) |
| `last_scan_at` | Timestamp of the latest associated scan |
| `last_scan_status` | `success` or `failed` |
| `last_scan_summary` | `{ total, healthy, warning, failed }` device counts |

**v1 behavior:** scans always execute on the local API process. The `address` field and reachability status prepare for remote agents; associating a scan with `machine_id` stores per-host snapshots for dashboard context.

Persistence file: `{data_dir}/machines.json` with `machines` and `latest_scans` sections.

## Run Locally

```bash
pip install -e .[api]
sudo cdi-health-api --host 127.0.0.1 --port 8844 --data-dir ./.cdi-health
```

Development mode without root (mock/testing only):

```bash
cdi-health-api --allow-non-root --mock-data src/cdi_health/mock_data
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
ExecStart=/usr/local/bin/cdi-health-api --host 127.0.0.1 --port 8844 --data-dir /var/lib/cdi-health
Restart=on-failure
Environment=CDI_HEALTH_API_TOKEN=replace-me

[Install]
WantedBy=multi-user.target
```
