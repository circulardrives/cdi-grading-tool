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
- `cdi_health.api.discovery`: LAN subnet scanning and CDI Health API probing.
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
- `GET /api/v1/discover` — scan LAN for CDI APIs (optional `subnet`, `port`, `timeout_seconds`)
- `POST /api/v1/discover` — same scan with JSON body (`subnet`, `subnets`, `port`, `timeout_seconds`, `probe_token`)
- `POST /api/v1/selftests`
- `GET /api/v1/selftests/status`
- `POST /api/v1/selftests/abort`

### Self-test status payload

`GET /api/v1/selftests/status` returns one row per NVMe controller with live
progress and the latest entries from the NVMe device self-test log (Log Page
0x06 via `nvme self-test-log`).

Each device object includes:

| Field | Description |
| ----- | ----------- |
| `device` | Controller path, e.g. `/dev/nvme0` |
| `supported` | Whether the controller reports self-test support |
| `status` | Human-readable current status string |
| `in_progress` | Whether a self-test is currently running |
| `progress_percent` | Optional progress percentage while running |
| `passed` / `failed` / `aborted` | Outcome flags from the latest log entry |
| `latest_result` | Latest completed entry: `result_code`, `result`, `test_type_code`, `test_type` |
| `recent_results` | Up to five recent log entries with the same shape |
| `current_completion` | Current completion percentage from the log header |
| `last_test_date` | Timestamp when available |

`POST /api/v1/selftests` creates an async job. With `wait: false` (default),
the job completes after tests are **started**; poll `GET /api/v1/selftests/status`
or `GET /api/v1/jobs/{job_id}` until `in_progress` is false, then read
`latest_result` for pass/fail details.
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

## LAN Discovery

Browsers cannot port-scan the LAN directly. Discovery runs on whichever machine hosts
`cdi-health-api` (technician laptop, jump host, or grading bench PC). Point the dashboard
at that API; the **Hosts & Scans** page triggers discovery through the backend.

**Flow**

1. Derive subnet(s) from local IPv4 interfaces when `subnet` is omitted (defaults to /24 per interface).
2. TCP-probe each address on port **8844** (configurable) with parallel workers (~1–2s timeout per host).
3. For open ports, `GET http://{ip}:{port}/api/v1/health` (optional `X-API-Token` via `probe_token` or `CDI_HEALTH_API_TOKEN`).
4. Return discovered hosts with health payload and `already_registered` when the address matches the fleet registry.

**Security / limits**

- Requires the same auth as other mutating endpoints when `CDI_HEALTH_API_TOKEN` is set.
- Only private/link-local IPv4 ranges (`10/8`, `172.16/12`, `192.168/16`, `169.254/16`).
- Max **256** addresses per subnet (/24 or smaller), max **4** subnets per request.
- Rate limit: one discovery scan every **10** seconds per API process.

**Example**

```bash
curl -s -X POST http://127.0.0.1:8844/api/v1/discover \
  -H 'Content-Type: application/json' \
  -d '{"subnet":"192.168.0.0/24"}'
```

Response shape:

```json
{
  "scanned_subnets": ["192.168.0.0/24"],
  "port": 8844,
  "hosts_scanned": 254,
  "open_ports": 1,
  "duration_ms": 842,
  "found": [
    {
      "address": "192.168.0.12:8844",
      "ip": "192.168.0.12",
      "port": 8844,
      "hostname": "grading-01.local",
      "health": { "status": "ok", "is_root": true },
      "cdi_api": true,
      "already_registered": false
    }
  ]
}
```

**Limitations**

- IPv6 and non-private subnets are rejected.
- APIs bound only to `127.0.0.1` on remote hosts are not reachable from the network.
- Reverse DNS may be missing; the dashboard uses IP as the default display name.
- Discovery finds listening APIs; it does not execute scans on remote hosts (v1 scans remain local).

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
WorkingDirectory=/var/lib/cdi-health
ExecStart=/usr/local/bin/cdi-health-api --host 127.0.0.1 --port 8844 --data-dir /var/lib/cdi-health
Restart=on-failure
Environment=CDI_HEALTH_API_TOKEN=replace-me

[Install]
WantedBy=multi-user.target
```
