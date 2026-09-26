# CDI Dashboard Backend Architecture

## Runtime Model

- Backend runs locally on the same host that has attached drives.
- One dashboard can also drive a fleet: registered machines with an `address` are other benches running their own `cdi-health-api`; scans and NVMe self-tests for them are forwarded over the LAN, and reports can be built from their saved scans (see [Remote Hosts](#remote-hosts) and [Reports](#reports)).
- Backend binds to `127.0.0.1` by default and is not intended for public hosting.
- Backend process runs as root for real device access (`smartctl`, `nvme`, `sg3-utils`).
- Static token auth via `CDI_HEALTH_API_TOKEN` (or `--api-token`) is **required** whenever `--host` is not loopback, unless lab mode (`--no-auth` / `CDI_HEALTH_API_NO_AUTH=1`) is on; the process fails fast at startup otherwise.
- Host registry, scan snapshots, and generated reports persist under a configurable data directory (default: `./.cdi-health`, env `CDI_HEALTH_DATA_DIR`, or `--data-dir`). Reports are constrained to `{data_dir}/reports/`. Scan history is stored as one JSON file per scan under `{data_dir}/scan-history/`.

## Components

- `cdi_health.api.app`: FastAPI app and HTTP routes.
- `cdi_health.api.services`: Scan, self-test, and report service layer.
- `cdi_health.api.machines`: JSON-backed fleet host registry and scan association.
- `cdi_health.api.history`: Append-only scan history (one JSON snapshot per successful scan).
- `cdi_health.api.reports_index`: Persisted index of generated reports (`{data_dir}/reports/index.json`).
- `cdi_health.api.discovery`: LAN subnet scanning and CDI Health API probing.
- `cdi_health.api.remote`: Stdlib HTTP client that forwards scans, self-tests, jobs, and health checks to remote benches.
- `cdi_health.api.jobs`: In-memory async job tracking for long-running actions.
- `cdi_health.api.security`: Root enforcement, bind-host token checks, and token validation.

## HTTP Endpoints

- `GET /api/v1/health` — always returns `{status, version, hostname}` (`hostname` is the bench's own `socket.gethostname()`, e.g. `bench-01`; not sensitive, so it is in the minimal payload too); full diagnostics when auth is disabled, or with a valid token / loopback client when auth is enabled
- `POST /api/v1/scan` — optional `machine_id` associates the scan with a registered host (unknown id → 404); when that machine has an `address` the scan **runs on the remote host** (see [Remote Hosts](#remote-hosts)); optional `grading_profile` (`binary` | `abcdf`, like `--grading-profile`); successful scans are appended to scan history. Responses carry `machine_id`, `executed_on` (`"local"` | `"remote"`), and `remote_address` (remote only)
- `GET /api/v1/devices` — optional `machine_id` returns cached scan for that host; `refresh=true` rescans (forwarded to the remote host when the machine has an `address`) and appends history
- `GET /api/v1/fleet/devices` — aggregated drives across all remote hosts plus this API's own latest scan; `refresh=true` rescans every remote host first
- `GET /api/v1/history` — list persisted scans (`limit`/`offset`; optional `machine_id` filter); newest first
- `GET /api/v1/history/{id}` — full scan snapshot (devices + summary)
- `DELETE /api/v1/history/{id}` — delete one persisted scan (`{"deleted": true, "id": "..."}`)
- `DELETE /api/v1/history` — clear all persisted scans (`{"deleted": <count>}`)
- `GET /api/v1/machines` — list registered grading hosts (`limit`/`offset` pagination)
- `POST /api/v1/machines` — register a host
- `GET /api/v1/machines/{id}` — host detail
- `PATCH /api/v1/machines/{id}` — update host metadata (`api_token`: omit = unchanged, `""` = clear)
- `POST /api/v1/machines/{id}/check` — probe the remote host with its token; updates `status` / `remote_version` / `remote_hostname`
- `DELETE /api/v1/machines/{id}` — remove host and cached scan snapshot
- `GET /api/v1/discover` — return cached last discovery result (no side effects; 404 if none)
- `POST /api/v1/discover` — run LAN scan (`subnet`, `subnets`, `port`, `timeout_seconds`, `probe_token`); 429 while a scan is in progress or within cooldown
- `POST /api/v1/selftests` — optional body `machine_id` (remote host → forwarded; see [Remote Hosts](#remote-hosts))
- `GET /api/v1/selftests/status` — optional `device`, `machine_id` query params
- `POST /api/v1/selftests/abort` — body `device`, optional `machine_id`

**Hardware lock.** Only one drive-touching operation runs at a time: `POST /api/v1/scan`, `GET /api/v1/devices` when it rescans (`refresh=true` or empty cache), `POST /api/v1/reports` with `source: "scan"`, and the start phase of `POST /api/v1/selftests`. Scans and self-test calls forwarded to a remote host, and reports built from saved scans (`source: "fleet"` / `"history"`), do **not** take this API's lock; the remote API holds its own and answers 409 when busy, which is passed through. A request that arrives while another holds the lock gets **HTTP 409** (`{"detail": "Drive hardware is busy ..."}`) instead of queueing; retry after the running operation completes. Self-test `wait` polling, status, and abort do not take the lock.

**Scan payload.** Scan responses (and `GET /api/v1/devices`) include `grading_profile` (profile actually applied) and `summary: {total, healthy, warning, failed, ungraded}`. Devices carry the same Revert §13/§15 fields as CLI JSON and reports (`grading_status`, `final_grade`, `fail_reason_codes`, `warning_flags`, `ungraded_reasons`, `recommended_use`, ...). UNGRADED drives (e.g. security-locked, unreadable SMART) have `grading_status: "UNGRADED"`, `final_grade`/`health_grade: "UNGRADED"`, `health_score: null`, and are counted in `summary.ungraded`, **not** `failed`. `POST /api/v1/reports` also accepts `grading_profile`.

**Path allowlist.** Request `mock_data`, `mock_file`, and `config` paths must resolve (after symlinks) inside the packaged `mock_data/` or `config/` directories, the API data directory, `/etc/cdi-health`, the server's `--mock-data` default, or an extra root listed in `CDI_HEALTH_API_ALLOWED_DATA_PATHS` (`:`-separated). Anything else returns **400** `Path is outside the allowed data directories`.

**Per-request thresholds.** A scan/report `config` path is applied only to that request (the process-global thresholds are never replaced). Without `config`, the packaged `thresholds.yaml` defaults apply, matching the CLI.

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
`latest_result` for pass/fail details. For a remote host pass the same
`machine_id` on every call (start, status, jobs, abort).
- `GET /api/v1/jobs` — list jobs (`limit`/`offset`, optional `machine_id`; completed jobs expire via TTL/max-size eviction)
- `GET /api/v1/jobs/{job_id}` — optional `machine_id` (required to poll a job that runs on a remote host)
- `POST /api/v1/reports` — generate a report (see [Reports](#reports)); writes only under `{data_dir}/reports/` (basename or in-dir path)
- `GET /api/v1/reports` — list generated reports, newest first (persisted index)
- `GET /api/v1/reports/{filename}` — serve a generated report from the reports directory (`download=true` → attachment)

## Reports

`POST /api/v1/reports` body:

| Field | Description |
| ----- | ----------- |
| `format` | `html` (default), `pdf`, or `csv` |
| `source` | `scan` (default): fresh scan of **this** API's drives, exactly as before (takes the hardware lock; honours `ignore_*`, `device`, `config`, `mock_data`, `mock_file`, `grading_profile`). `fleet`: the latest stored scan of every host — the same set as `GET /api/v1/fleet/devices` (each remote machine's cached scan plus this API's own latest scan when it has devices). `history`: the scan-history entries listed in `history_ids` |
| `history_ids` | Required for `source: "history"`: 1–50 ids from `GET /api/v1/history` (duplicates ignored). Missing / empty / more than 50 → **400**; any unknown id → **404** |
| `output_file` | Optional basename under `{data_dir}/reports/`; default `cdi-report-YYYYMMDD-HHMMSS.<format>` (a `-2`, `-3`… suffix is added when that name exists) |

**Saved-scan reports** (`fleet` / `history`) never rescan, never take the hardware lock, and ignore the fresh-scan options (`ignore_*`, `device`, `config`, `mock_*`). When the selected scans contain no devices the request fails with **400** `No saved scans to report on — run Scan all hosts first`.

**Recorded grades are preserved.** Devices in stored scans already carry `health_score`, `health_grade` / `final_grade`, `health_deductions`, certification fields, etc. Saved-scan reports render those as recorded (`ReportGenerator(preserve_grades=True)`); they are **not** re-scored with the current thresholds. The `cdi-health report` CLI and `source: "scan"` score fresh devices as before.

**Host columns.** Saved-scan reports tag every device with its host, and the HTML (simple and advanced tables) and CSV gain **Host** and **Scanned at** (`YYYY-MM-DD HH:MM UTC`) columns right after **Serial**. Fresh single-host scans keep the original layout. The HTML header shows a **Source** line: `Saved scans — bench-01 (2026-09-26 08:59 UTC), bench-02 (…)` or `Fresh scan on this bench`. Scan-history entries of a deleted machine are labelled `Removed host <id-prefix>`; scans of this API's own drives are `Local API`.

Response (`ReportResponse`):

```json
{
  "generated_at": "2026-09-26T12:00:05+00:00",
  "output_file": "/var/lib/cdi-health/reports/cdi-report-20260926-120005.html",
  "filename": "cdi-report-20260926-120005.html",
  "format": "html",
  "devices_count": 16,
  "source": "fleet",
  "hosts": [
    { "name": "bench-01", "machine_id": "…", "scanned_at": "2026-09-26T08:59:00+00:00", "device_count": 8 },
    { "name": "bench-02", "machine_id": "…", "scanned_at": "2026-09-26T09:30:00+00:00", "device_count": 8 }
  ]
}
```

For `source: "scan"`, `hosts` is a single `{"name": "Local API", "machine_id": null, "scanned_at": <generated_at>, …}` entry.

**Report index.** Every generated report is recorded in `{data_dir}/reports/index.json` (mode **0600**), so `GET /api/v1/reports` and downloads survive API restarts. `GET /api/v1/reports` returns `[{filename, format, generated_at, source, devices_count, hosts}]`, newest first, skipping entries whose file was removed. Only the newest **200** records are kept; older records are dropped from the index but their files are not deleted (they can still be downloaded by name).

**PDF** needs `weasyprint` (`GET /api/v1/health` → `weasyprint_available`); without it `format: "pdf"` fails with **400** `Report failed`.

## Host Registry Model

Each machine (host) record includes:

| Field | Description |
| ----- | ----------- |
| `id` | UUID primary key |
| `name` | Display name (required) |
| `hostname` | Host identifier (required) |
| `address` | Optional `ip`, `host:port`, or `http://host:port` of the host's `cdi-health-api` (port defaults to **8844**). Empty = registry-only machine scanned by this API |
| `location` | Optional rack / data-center label |
| `notes` | Optional technician notes |
| `status` | `unknown`, `reachable`, `unreachable`, or `auth_failed` |
| `has_api_token` | `true` when a remote API token is stored (the token itself is never returned) |
| `remote_version` | Remote API version from the last successful `/check` (`null` until checked) |
| `remote_hostname` | Hostname the remote bench reports in its `/health` payload, recorded by `/check` (`null` until checked, or for older benches). The dashboard shows it as the bench name when `name` is empty or just the address |
| `last_seen_at` | Last time the host was observed (successful scan or check) |
| `last_scan_at` | Timestamp of the latest associated scan |
| `last_scan_status` | `success` or `failed` |
| `last_scan_summary` | `{ total, healthy, warning, failed, ungraded }` device counts |

`POST` / `PATCH /api/v1/machines` also accept a **write-only** `api_token` (the remote host's `X-API-Token`). No response ever contains it: machine list/detail, check results, and anything embedding a machine only expose `has_api_token`. On `PATCH`, omitting `api_token` leaves it unchanged and `""` clears it.

Persistence file: `{data_dir}/machines.json` with `machines` and `latest_scans` sections. Remote tokens are stored there **in plaintext**; the file is written with mode **0600** (owner read/write only, tightened on load for older stores). Protect the data directory accordingly.

## Remote Hosts

A machine with an `address` is another grading bench running its own `cdi-health-api` (with its own `CDI_HEALTH_API_TOKEN`, or in lab no-auth mode). A technician laptop can run one dashboard + local API and see drives from every bench.

**Auth mode.** `GET /api/v1/health` always includes `auth_mode`: `"token"` (requests need `X-API-Token`; unauthenticated callers get only `{status, version, auth_mode}`) or `"none"` (lab mode via `--no-auth` / `CDI_HEALTH_API_NO_AUTH=1`; the full payload is public and `api_token_enabled` is `false`). Discovery results carry each host's health payload, and `/machines/{id}/check` records it as the machine's `remote_auth`. No token needs to be stored for a `remote_auth: "none"` host.

**Scan forwarding** (`POST /api/v1/scan` with that `machine_id`, or `GET /api/v1/devices?machine_id=…&refresh=true`):

1. The request body is forwarded to `POST <remote>/api/v1/scan` **without** `machine_id`, `mock_data`, `mock_file`, and `config` (local ids and file paths are never sent). `ignore_*`, `device`, and `grading_profile` are kept.
2. The host's stored token is sent as `X-API-Token` (no header when none is stored).
3. The remote `ScanResponse` is returned with `machine_id`, `executed_on: "remote"`, and `remote_address` added.
4. The result is persisted like a local scan: a scan-history entry with `machine_id`, and the machine's `last_scan_*`, `last_seen_at`, and `status: "reachable"`. Remote results never replace this API's own latest scan (`GET /api/v1/devices` without `machine_id`).

Timeouts: health/check **5 s**; scan **300 s** (override with `CDI_HEALTH_REMOTE_SCAN_TIMEOUT`, seconds).

**Error mapping** (the machine `status` is updated too):

| Remote outcome | HTTP | `detail` | Machine status |
| -------------- | ---- | -------- | -------------- |
| Connection refused / unreachable / DNS failure | 502 | `Host '<name>' is unreachable at <address>` | `unreachable` |
| Timeout | 504 | `Host '<name>' timed out` | `unreachable` |
| 401 / 403 | 502 | `Host '<name>' rejected the API token` | `auth_failed` |
| 409 (remote hardware busy) | 409 | remote `detail` passed through | `reachable` |
| Other 4xx | same code | remote `detail`, sanitized (single line, ≤ 200 chars) | `reachable` |
| 5xx, or a response that is not a valid scan | 502 | `Host '<name>' scan failed` / `… returned an invalid scan response` | `reachable` |

The same mapping applies to forwarded self-test / job calls (described below).

**Self-test forwarding.** `POST /api/v1/selftests`, `POST /api/v1/selftests/abort` (body `machine_id`), and `GET /api/v1/selftests/status`, `GET /api/v1/jobs`, `GET /api/v1/jobs/{job_id}` (query `machine_id`) are forwarded to the same path on the remote host when `machine_id` names a machine with an `address`:

1. `machine_id` is stripped from the body / query; everything else (`device`, `test_type`, `wait`, `limit`, `offset`, …) is forwarded unchanged. The stored token is sent as `X-API-Token` (no header when none is stored).
2. The remote JSON is returned unchanged plus `machine_id` (added to each `JobResponse`, and to the status / abort objects). Remote job ids are opaque: poll `GET /api/v1/jobs/{job_id}?machine_id=…` with the same `machine_id`.
3. This API's hardware lock and self-test worker pool are not used; the job runs on the remote.
4. Timeout **30 s** per call (starting a test returns immediately). Errors map exactly as in the scan table above (a 5xx or non-JSON reply is `Host '<name>' request failed` / `… returned an invalid response`; the remote's 404 `Job not found` is passed through). The machine `status` becomes `unreachable` / `auth_failed` on failure and `reachable` on the next success.

A `machine_id` of a machine **without** an address runs locally (as without `machine_id`); an unknown `machine_id` is **404** `Machine not found`. The dashboard's self-test page also reads `GET /api/v1/devices?machine_id=…` (the host's cached scan) for serial numbers. Reports use stored scans instead of forwarding: see [Reports](#reports).

**Private-network restriction.** Calls are only forwarded to private, link-local, or loopback IPv4 addresses (`10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `127/8`) or hostnames whose every resolved address is in those ranges. Anything else (public IPs, IPv6, `https://` for now, userinfo) returns **400** `Remote host address must be on a private network` (or a specific invalid-address message). The resolved IP is pinned for the request (with the original `Host` header) so DNS rebinding cannot redirect it; redirects are never followed and `HTTP(S)_PROXY` is ignored, so the token only goes to the validated address. Transport is plain HTTP today (tokens cross the LAN unencrypted; trusted lab networks only); the client is structured so `https://` can be added later.

### `POST /api/v1/machines/{id}/check`

Sends `GET <remote>/api/v1/health` and then `GET <remote>/api/v1/jobs?limit=1`, both with the stored token. `/health` never returns 401 (unauthenticated callers just get the minimal `{status, version}` payload, and loopback callers always get the full one), so the authenticated `jobs` probe is the reliable token check: 401/403 there means `auth_failed`.

```json
{
  "machine": { "id": "…", "status": "reachable", "remote_version": "0.9.0", "remote_hostname": "bench-01", "has_api_token": true, "…": "…" },
  "health": { "status": "ok", "version": "0.9.0", "hostname": "bench-01", "is_root": true, "api_token_enabled": true },
  "error": null
}
```

Reachability problems are reported with HTTP 200, `status` set to `unreachable` / `auth_failed`, and a human-readable `error` (`health` is the remote payload when it was obtained, else `null`). Only a missing machine (404) or a machine with no / non-private address (400) fail the request.

### `GET /api/v1/fleet/devices.csv`

The drive list as CSV with **the same columns, in the same order, as `cdi-health scan -o csv`** (the CLI's `CSVFormatter`), built from each bench's latest saved scan — no rescan, grades exactly as recorded. The all-benches export adds one trailing `bench` column; `?machine_id=<id>` (or `local` for this API's own scan) exports a single bench with no extra column. `Content-Disposition: attachment; filename="cdi-drives-<bench|all-benches>-<YYYYmmdd-HHMM>.csv"`. 404 when the bench is unknown or has no saved scan.

### `GET /api/v1/fleet/devices`

Aggregates every registered machine **with an address**, plus this API's own latest cached scan as a host named `"Local API"` (`machine_id: null`) when it has at least one device. Registry-only machines (no address) are not included. Without `refresh`, cached per-host scans are used. With `refresh=true`, all remote hosts are rescanned first (at most **4** concurrently; each result is persisted as above). Per-host failures are reported in `hosts[].error` and never fail the request; a host whose refresh failed still contributes its previous cached scan (check `scanned_at`).

```json
{
  "hosts": [
    {
      "machine_id": "…",
      "name": "Bench 01",
      "address": "192.168.0.12:8844",
      "status": "reachable",
      "scanned_at": "2026-09-26T12:00:00+00:00",
      "summary": { "total": 8, "healthy": 7, "warning": 0, "failed": 1, "ungraded": 0 },
      "device_count": 8,
      "error": null,
      "executed_on": "remote"
    }
  ],
  "devices": [
    { "…device fields as in ScanResponse.devices…": "", "machine_id": "…", "machine_name": "Bench 01", "host_address": "192.168.0.12:8844" }
  ],
  "summary": { "total": 8, "healthy": 7, "warning": 0, "failed": 1, "ungraded": 0 },
  "generated_at": "2026-09-26T12:00:05+00:00"
}
```

## Scan History

Successful scans (via `POST /api/v1/scan` or a refreshing `GET /api/v1/devices`) are also written under `{data_dir}/scan-history/` as one JSON file per scan (`YYYYMMDD-HHMMSS-<8hex>.json`). Each file stores the full device snapshot plus `grading_profile`, summary counts (including `ungraded`), and grade tallies (UNGRADED drives tally under `"UNGRADED"`, never `"F"`). Entries written before this field existed read back with `ungraded: 0`. The dashboard **History** page lists these entries and opens a read-only drive table for any past scan.

Per-drive longitudinal timelines (metric deltas across scans for one serial) are deferred to a follow-up.

## LAN Discovery

Browsers cannot port-scan the LAN directly. Discovery runs on whichever machine hosts
`cdi-health-api` (technician laptop, jump host, or grading bench PC). Point the dashboard
at that API; the **Hosts & Scans** page triggers discovery through the backend.

**Flow**

1. Derive subnet(s) from local IPv4 interfaces when `subnet` is omitted (defaults to /24 per interface).
2. TCP-probe each address on port **8844** (configurable) with parallel workers (~1–2s timeout per host).
3. For open ports, `GET http://{ip}:{port}/api/v1/health` (`X-API-Token` is sent **only** when the request supplies an explicit `probe_token`; the bench's own `CDI_HEALTH_API_TOKEN` is never sent, since probes are plain HTTP to every open host. The unauthenticated `{status, version}` payload is enough to identify a CDI bench).
4. Return discovered hosts with health payload (newer benches include their own `hostname` there, even unauthenticated; the top-level `hostname` is reverse DNS) and `already_registered` when the address matches the fleet registry.

**Security / limits**

- Requires the same auth as other mutating endpoints when `CDI_HEALTH_API_TOKEN` is set.
- Only private/link-local IPv4 ranges (`10/8`, `172.16/12`, `192.168/16`, `169.254/16`).
- Max **256** addresses per subnet (/24 or smaller), max **4** subnets per request.
- Concurrency: only one discovery scan at a time (429 while in progress); cooldown of **10** seconds between scans.

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
      "health": { "status": "ok", "version": "0.9.5", "hostname": "grading-01", "auth_mode": "token" },
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
- Discovery only finds listening APIs. Register a found host (with its `api_token`) to scan it; see [Remote Hosts](#remote-hosts).

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

Use the shipped unit `deploy/systemd/cdi-health-api.service` (installed by the
`.deb` as `/usr/lib/systemd/system/cdi-health-api.service`). It runs as root
(raw device ioctls) but is sandboxed: `ProtectSystem=strict` with
`ReadWritePaths=/var/lib/cdi-health /var/cache/cdi-health`, `ProtectHome=true`,
`PrivateTmp=true`, `NoNewPrivileges=true`, and no `PrivateDevices=` so `/dev`
stays reachable. Put the token in `/etc/default/cdi-health-api`
(`deploy/systemd/cdi-health-api.env.example`), not in the unit. If you change
`--data-dir`, add the new path to `ReadWritePaths=` with a drop-in.
