# NAM frontend

Next.js (App Router) + TypeScript. Consumes **nam-api** only — no direct DB or agent access.

## Setup

```bash
pnpm install
cp .env.example .env
```

From the repo root, run the full stack (DB, API, agentic, front):

```bash
just app
```

Or run the front alone (API must already be up):

```bash
just front
# or: pnpm dev
```

App: http://localhost:3000

## Environment

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | nam-api base URL (default `http://localhost:8000`) |

Secrets stay in the **repo root** `.env` (Python backend) — not here.

## API client (Orval)

Hooks and types are generated from nam-api OpenAPI:

```bash
# nam-api must be running on NEXT_PUBLIC_API_URL
pnpm orval
```

Output: `src/api/generated/` (do not edit manually). Custom fetch mutator: `src/api/mutator.ts`.

## Routes

| Route | Description |
|-------|-------------|
| `/` | Redirects to onboarding or dashboard |
| `/onboarding` | 3-step profile setup → `POST /setup` |
| `/dashboard` | Portfolio view, add BUY positions |

Profile guard: `GET /profile` 404 → onboarding, 200 → app shell.
