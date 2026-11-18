# CDI Health Dashboard

Vite + React technician console for the CDI Health local API. Built with [shadcn/ui](https://ui.shadcn.com) (radix-luma preset) in a bun monorepo.

**Release:** use Docker image `ghcr.io/circulardrives/cdi-health-dashboard:latest` (or pin a semver tag) or build from this repo.

## Structure

```
dashboard/
├── apps/web/          # Vite SPA (technician UI)
└── packages/ui/       # Shared shadcn components
```

## Quick start (Docker — recommended)

From the repository root:

```bash
./scripts/docker-up.sh

# Live scans via one remote bench
./scripts/docker-up.sh --bench 192.168.0.74

# Build from this clone
./scripts/docker-up.sh --build
```

Open http://127.0.0.1:3000

- **Discover** → subnet `192.168.0.0/24` to find `cdi-health-api` on the network.
- **Mock data** (toggle in the app header) is **off by default**; enable for fixture demos only.

Images (multi-arch):

- `ghcr.io/circulardrives/cdi-health-api:latest`
- `ghcr.io/circulardrives/cdi-health-dashboard:latest`

See [Team testing](../docs/TEAM_TESTING.md) and [Technician deployment](../docs/TECHNICIAN_DEPLOYMENT.md).

## Local development (bun)

Requires [bun](https://bun.sh) 1.3+.

```bash
cd dashboard
cp apps/web/.env.example apps/web/.env.local
bun install
bun run dev
```

Or all-in-one mock from repo root:

```bash
./scripts/start-local-mock.sh
```

Live scans are the default; enable **Mock data** in the app header for fixtures.

## Environment

Copy `apps/web/.env.example` to `apps/web/.env.local`.

| Variable | Purpose |
| --- | --- |
| `VITE_CDI_API_BASE_URL` | Fetch base path (`/api/cdi` in dev) |
| `VITE_CDI_API_PROXY_TARGET` | Vite proxy upstream (default `127.0.0.1:8844`) |
| `CDI_HEALTH_API_TOKEN` | Injected as `X-API-Token` by the Vite dev/preview proxy (server-side only; not bundled). Legacy `VITE_CDI_API_TOKEN` is still accepted |
| `VITE_CDI_MOCK_DATA_PATH` | Path sent to API when **Use mock data** is enabled |
| `VITE_CDI_DISCOVER_SUBNET` | Default subnet placeholder on Discover |

In Docker/nginx production mode, the UI uses `/api/cdi` on the same origin; nginx proxies to the API container or remote bench and adds `X-API-Token` from `CDI_HEALTH_API_TOKEN`. The browser never holds the token.

## Adding components

```bash
cd packages/ui
bunx --bun shadcn@latest add <component> -y
```

Import from `@workspace/ui/components/<name>` in the web app.

## Production build

```bash
cd dashboard
bun run build
bun run start   # serves apps/web/dist via vite preview
```

For production without bun on the host, use Docker (`deploy/docker/`) or GHCR compose.

## Static demo

A public, API-free demo of the dashboard with sample drives on three benches
(`bench-01` NVMe servers, `bench-02` HDD chassis, `bench-03` mixed intake). It
is plain static files, so it can be hosted anywhere (Cloudflare Pages below).

```bash
# From the repository root: regenerate sample data, then build with VITE_DEMO=1
./scripts/build-demo.sh               # --no-data reuses the committed data

bunx serve -s dashboard/apps/web/dist-demo    # preview with SPA fallback

npx wrangler deploy -c dashboard/apps/web/wrangler.demo.jsonc
```

- **Data.** `scripts/generate_demo_data.py` takes smartctl fixtures from
  `src/cdi_health/mock_data` and `tests/fixtures/revert_standard`, anonymizes
  them (serials, WWN / EUI-64 / FGUID replaced with stable hash-derived values;
  vendor placeholders replaced), and runs them through the real grader and API
  endpoints in-process. Grades, reasons, CSVs and the HTML reports are exactly
  what CDI Health produces for those drives. The output is committed under
  `apps/web/src/demo/data/`; rerun the script after grading changes.
- **Backend.** With `VITE_DEMO=1`, `src/lib/api.ts` sends every API call to
  `src/demo/backend.ts`, which answers from that data in the browser — no
  network requests. Scans, reports and self-tests (which pass after ~20 s)
  are simulated in memory; benches added or removed live in `sessionStorage`,
  so the demo resets when the tab closes.
- **Build.** Normal builds are unaffected: `__CDI_DEMO__` is a build-time
  constant, so the demo backend and data are never bundled. The demo build
  writes `dist-demo/` (SPA fallback comes from `wrangler.demo.jsonc`) and the page title
  "CDI Health — Demo".
