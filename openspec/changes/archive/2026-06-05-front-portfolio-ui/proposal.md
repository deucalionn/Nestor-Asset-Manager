# Front portfolio UI

## Why

NAM has a working backend (profile setup, indices, transactions, positions) but no user-facing interface. A Next.js front with type-safe API clients is needed so users can onboard, view their portfolio, and add holdings — the minimum viable product before chat and agent features.

## What Changes

- Configure **Orval** in `front/` to generate React Query hooks and TypeScript types from **nam-api** OpenAPI only (`:8000`)
- Implement a **3-step onboarding wizard** (identity → strategy → goals) with back navigation, calling `POST /setup`
- Implement **app shell** with left sidebar (Dashboard, Chat placeholder) and Stripe-inspired minimal layout
- Implement **dashboard**: positions list, cost basis summary, add index + open position via `POST /indices` + `POST /transactions` (BUY)
- Gate routes: no profile → onboarding; profile exists → dashboard
- Design system: white background, `#68B3AE` accent, clean typography and spacing

**Out of scope (this change):**

- WebSocket chat (sidebar link shown as disabled / coming soon)
- Direct calls to nam-agentic (`:8001`)
- Unrealized P/L with live market prices (API has no `current_price` yet — show placeholder)
- Auth, multi-user, recommendations, analyses

## Capabilities

### New Capabilities

- `front-orval-client`: Orval config, generated API client, env wiring to nam-api
- `front-onboarding`: 3-step first-run wizard and profile bootstrap
- `front-app-shell`: Layout, sidebar navigation, routing guards, design tokens
- `front-dashboard`: Portfolio dashboard, positions display, add index/transaction flows

### Modified Capabilities

- (none — backend API unchanged)

## Impact

| Area | Impact |
|------|--------|
| `front/` | Orval, pages, components, TanStack Query, styling |
| `nam-api` | Consumer only — no API code changes required |
| `nam-agentic` | None — front never calls agentic |
| `openspec.md` | Optional appendix update for front module (deferred) |
