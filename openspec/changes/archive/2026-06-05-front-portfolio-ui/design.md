# Design — front portfolio UI

## Context

- **Front**: Next.js 16 (App Router) + TypeScript + pnpm in `front/`
- **API**: nam-api on `:8000` — singleton user, no auth
- **Agentic**: `:8001` internal only; front MUST NOT call it
- **Existing endpoints** used in v1 UI:

| Method | Route | UI use |
|--------|-------|--------|
| POST | `/setup` | Onboarding finalize |
| GET | `/profile` | Route guard (404 = onboarding) |
| GET/POST | `/indices` | List + register new index |
| GET | `/positions` | Dashboard holdings |
| POST | `/transactions` | BUY to open/increase position |

Positions are **not** created directly — a BUY transaction recalculates positions server-side.

## Goals / Non-Goals

**Goals:**

- Type-safe API access via Orval-generated hooks (single OpenAPI source: nam-api)
- First-run onboarding in 3 steps with back/forward navigation
- Dashboard showing positions with cost basis; clear path to add an index and a BUY
- Minimal, Stripe-inspired UI (white + `#68B3AE`)
- Sidebar with Dashboard (active) and Chat (disabled until WS exists)

**Non-Goals:**

- Chat implementation, Orval on agentic, market price enrichment, SELL flow in UI (can be follow-up)
- i18n, dark mode, mobile-first polish beyond responsive basics

## Decisions

### 1. Orval targets nam-api only

```text
Front ──Orval/React Query──► nam-api OpenAPI (:8000)
                              (never nam-agentic)
```

- **Input**: `http://localhost:8000/openapi.json` (or env `NEXT_PUBLIC_API_URL`)
- **Output**: `front/src/api/generated/` (gitignored or committed — **commit generated code** for reproducible builds without running API)
- **Client**: `@tanstack/react-query` + `fetch` or `axios` mutator pointing at `NEXT_PUBLIC_API_URL`
- **Regenerate**: `pnpm orval` script when API schemas change

**Alternative rejected**: Hand-written fetch types — drifts from API.

### 2. Route guard via GET /profile

```text
App load → GET /profile
  ├─ 404 → /onboarding
  └─ 200 → /dashboard
```

No localStorage flag — server is source of truth for setup state.

### 3. Onboarding as 3-step client wizard

| Step | Fields | API field mapping |
|------|--------|-------------------|
| 1 — About you | firstname, date_of_birth | `UserCreate` |
| 2 — Strategy | strategy enum | `UserCreate.strategy` |
| 3 — Goals | goals (textarea), review summary | `UserCreate.goals` → `POST /setup` |

- State held in React context or URL step param (`?step=1|2|3`)
- **Back** preserves entered data; **Next** validates step locally before advancing
- Final step calls `POST /setup` once; on success redirect `/dashboard`

### 4. App shell layout

```text
┌──────────┬─────────────────────────────────┐
│ Sidebar  │  Main content                    │
│          │                                  │
│ Dashboard│  (page)                          │
│ Chat ⓘ   │                                  │
│          │                                  │
└──────────┴─────────────────────────────────┘
```

- Sidebar fixed ~240px, white/light gray border
- Active nav: `#68B3AE` left border or text accent
- Chat item: disabled + tooltip "Coming soon"

### 5. Design tokens

| Token | Value |
|-------|-------|
| `--color-background` | `#FFFFFF` |
| `--color-accent` | `#68B3AE` |
| `--color-text` | `#1a1a1a` (near black) |
| `--color-muted` | `#6b7280` |
| `--color-border` | `#e5e7eb` |
| Font | system-ui or Inter |

Stripe inspiration: generous whitespace, subtle borders, no heavy shadows, clear hierarchy, card-based sections.

### 6. Dashboard data model (client)

`PositionRead` returns `index_id`, `quantity`, `average_cost` — no index name.

- Fetch `GET /positions` + `GET /indices` and **join client-side** by `index_id`
- **Cost basis** per line: `quantity × average_cost`
- **Unrealized P/L**: display `—` with helper text until API exposes `current_price` (future change)

### 7. Add holding flow

Modal or slide-over:

1. Create index if needed (`POST /indices`: name, isin) OR pick existing
2. Submit BUY (`POST /transactions`: index_id, type BUY, price, quantity, date, fees optional)
3. Invalidate positions query → dashboard refreshes

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| OpenAPI unavailable at build time | Commit generated client; document `just back` before `pnpm orval` |
| No P/L without market data | Show cost basis + placeholder for gain/loss |
| CORS in dev | Configure nam-api CORS for `localhost:3000` |
| French UI copy vs English code | UI strings in French OK; identifiers/API enums stay English |

## Migration Plan

1. Add Orval + QueryProvider to `front/`
2. Add CORS middleware to nam-api if missing
3. Build onboarding → dashboard → add-holding
4. Manual test: fresh DB → onboarding → add index → BUY → see position

## Open Questions

- Commit generated Orval output vs generate in CI? **Recommendation: commit** for simpler local dev.
- SELL / edit transaction in UI? Defer to follow-up change.
