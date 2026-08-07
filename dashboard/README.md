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
- **Use mock data** (Discover → Demo mode) is **off by default**; enable for fixture demos only.

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

Live scans are the default; enable **Use mock data** on **Discover** for fixtures.

## Environment

Copy `apps/web/.env.example` to `apps/web/.env.local`.

| Variable | Purpose |
| --- | --- |
| `VITE_CDI_API_BASE_URL` | Fetch base path (`/api/cdi` in dev) |
| `VITE_CDI_API_PROXY_TARGET` | Vite proxy upstream (default `127.0.0.1:8844`) |
| `VITE_CDI_API_TOKEN` | Sent as `X-API-Token` when API auth is enabled |
| `VITE_CDI_MOCK_DATA_PATH` | Path sent to API when **Use mock data** is enabled |
| `VITE_CDI_DISCOVER_SUBNET` | Default subnet placeholder on Discover |

In Docker/nginx production mode, the UI uses `/api/cdi` on the same origin; nginx proxies to the API container or remote bench.

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
