# CDI Health Dashboard

Vite + React technician console for the CDI Health local API. Built with [shadcn/ui](https://ui.shadcn.com) (radix-luma preset) in a bun monorepo.

## Structure

```
dashboard/
├── apps/web/          # Vite SPA (technician UI)
└── packages/ui/       # Shared shadcn components
```

## Quick start

From the repository root with the API running:

```bash
cd dashboard
bun install
bun run dev
```

Open http://127.0.0.1:3000

Or use the all-in-one mock launcher from repo root:

```bash
./scripts/start-local-mock.sh
```

## Environment

Copy `apps/web/.env.example` to `apps/web/.env.local` and adjust as needed. The start script writes this file automatically.

| Variable | Purpose |
| --- | --- |
| `VITE_CDI_API_BASE_URL` | Fetch base path (`/api/cdi` in dev) |
| `VITE_CDI_API_PROXY_TARGET` | Vite proxy upstream (default `127.0.0.1:8844`) |
| `VITE_CDI_API_TOKEN` | Sent as `X-API-Token` when API auth is enabled |
| `VITE_CDI_USE_MOCK_DATA` | `1` to pass mock_data on scan/report calls |
| `VITE_CDI_MOCK_DATA_PATH` | Mock fixtures path relative to repo root |

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
