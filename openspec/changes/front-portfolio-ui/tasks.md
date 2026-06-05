# Tasks — front portfolio UI

## 1. API client (Orval)

- [x] 1.1 Add dependencies: `@orval/core`, `@tanstack/react-query`, optional `axios` or custom fetch mutator
- [x] 1.2 Create `front/orval.config.ts` pointing at `{NEXT_PUBLIC_API_URL}/openapi.json`
- [x] 1.3 Add `pnpm orval` script; output to `front/src/api/generated/`
- [x] 1.4 Add `QueryClientProvider` in root layout
- [x] 1.5 Configure API mutator with `NEXT_PUBLIC_API_URL` from `front/.env`

## 2. nam-api CORS (if needed)

- [x] 2.1 Add FastAPI CORS middleware allowing `http://localhost:3000` in dev
- [x] 2.2 Verify browser calls succeed from Next.js dev server

## 3. Design system & app shell

- [x] 3.1 Define CSS variables: white bg, `#68B3AE` accent, borders, typography
- [x] 3.2 Build `AppShell` component with sidebar (Dashboard, Chat disabled)
- [x] 3.3 Implement `(app)` layout wrapping dashboard routes
- [x] 3.4 Implement profile-based route guard (404 → onboarding, 200 → app)

## 4. Onboarding wizard

- [x] 4.1 Create `/onboarding` page with 3-step stepper UI
- [x] 4.2 Step 1: firstname + date_of_birth with client validation
- [x] 4.3 Step 2: strategy radio/select (enum values from generated types)
- [x] 4.4 Step 3: goals textarea + review summary + submit
- [x] 4.5 Wire Back/Next navigation preserving form state
- [x] 4.6 Call generated `POST /setup` hook; redirect to dashboard on success

## 5. Dashboard

- [x] 5.1 Create `/dashboard` page with welcome header (profile firstname)
- [x] 5.2 Fetch and join positions + indices; render holdings table/cards
- [x] 5.3 Show cost basis per row and total; P/L column as `—` placeholder
- [x] 5.4 Empty state with CTA when no positions

## 6. Add holding flow

- [x] 6.1 Modal/sheet: create index (`POST /indices`) or select existing
- [x] 6.2 Form: BUY transaction (price, quantity, date, fees)
- [x] 6.3 Submit via generated hook; invalidate positions query on success
- [x] 6.4 Handle API errors (409 duplicate ISIN, validation 422)

## 7. Verification

- [x] 7.1 Manual E2E: fresh DB → onboarding → add index → BUY → position visible
- [x] 7.2 Document in `front/README.md`: orval regen, env vars, dev with `just app`

## 8. Out of scope (follow-up)

- [ ] Chat page and WebSocket integration
- [ ] SELL / edit / delete transactions in UI
- [ ] Live unrealized P/L when API adds market prices
