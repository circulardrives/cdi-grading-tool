# CDI Technician Dashboard

Local Next.js dashboard for CDI Health backend operations.

## Features

- Trigger drive scans with protocol filters
- Start NVMe self-tests and poll async job state
- View health table and backend status
- Generate HTML/PDF reports

## Prerequisites

- Node.js 20+
- CDI backend running locally (`cdi-health-api`)

## Environment

Copy `.env.example` to `.env.local` and adjust if needed:

```bash
cp .env.example .env.local
```

`CDI_API_BASE_URL` defaults to `http://127.0.0.1:8844`.

## Run

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

## Production

```bash
npm run build
npm run start
```
