# NAM frontend

Next.js (App Router) + TypeScript. Consumes **nam-api** only — no direct DB or agent access.

## Setup

```bash
pnpm install
cp .env.example .env
pnpm dev
```

App: http://localhost:3000  
Backend must be running separately (`just back` from repo root).

## Environment

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | nam-api base URL (default `http://localhost:8000`) |

Secrets stay in the **repo root** `.env` (Python backend) — not here.
