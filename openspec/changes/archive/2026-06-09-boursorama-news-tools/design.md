# Design — boursorama-news-tools

## Context

- **Done**: `basics-tools` — memory/portfolio tools, `ToolRegistry`, `MarketScheduler` with `market.session` events, subagent prompts listing news tools as *planned*.
- **Gap**: Agents cannot read macro calendars, market headlines, or company-specific Boursorama pages during autonomous cycles.
- **User intent**: Ingest fixed Boursorama list pages on a schedule; let agents navigate deeper (e.g. Air Liquide → `1rPAI` → `/cours/actualites/1rPAI/`, `/cours/societe/chiffres-cles/1rPAI/`) when needed.
- **Constraints** (from `openspec.md`):
  - Ingestion runs inside `nam-agentic` lifespan (APScheduler) — no separate worker
  - Agents never write financial tables; news ingest writes `news_items` only
  - SSRF protection + domain whitelist for URL fetch tools
  - OOP tools via `BaseNamTool`; Pydantic v2 schemas; enums in `nam_db.enums`
  - No Playwright in v1 — `httpx` + HTML parsing + `trafilatura` + local LLM formatting

## Goals / Non-Goals

**Goals:**

- Persist structured news/calendar entries from six Boursorama list feeds (four daily calendars + two session news feeds)
- Run ingest on a predictable schedule without invoking the LLM
- Expose news tools aligned with `openspec.md` §9 (defer dedicated `GetCompanyFinancialsTool` to key-figures URL + `get_data_from_url`)
- Support **COMPANY** and **ETF** instruments via `indices.index_type` — different URL patterns and workflows
- Allow COMPANY agents to follow `/cours/actualites/{ticker}/`, `/cours/societe/chiffres-cles/{ticker}/`
- Allow ETF agents to fetch `/bourse/trackers/cours/composition/{ticker}/` and rely on **global** news (ingested + `/bourse/actualites/` hub)
- Idempotent upsert by canonical `source_url` to avoid duplicate rows on re-fetch

**Non-Goals:**

- Stock prices (`GetMarketPriceTool` remains separate / stub)
- Google or generic web search (use `SearchBoursoramaTool` instead)
- Browser automation (Playwright, Crawl4AI)
- pgvector embedding of news — **in scope**: `content_embedding` on upsert; semantic search via `get_financials_news(semantic_query=...)`
- nam-api REST endpoints for news
- US/Asia-specific news sources (Boursorama is EU/FR-first; same EU ingest schedule in v1)

## Decisions

### 1. Two-tier architecture: ingest vs agent read

```
APScheduler (ingest cron)
      │
      ▼
NewsIngestService ──httpx──► Boursorama list pages
      │
      ▼
PostgreSQL news_items
      ▲
      │ SELECT (filters)
GetFinancialsNewsTool ◄── agents during market.session
      │
      │ optional deep read
GetDataFromUrlTool ──httpx→trafilatura→LLM──► agent-ready Markdown
      ▲
      │ resolve ticker first
SearchBoursoramaTool ──httpx──► Boursorama site search
```

**Rationale:** Scheduled ingestion gives agents a **warm cache** at PRE_OPEN without N parallel scrapes per cycle. On-demand tools handle company-specific depth (user's Air Liquide example).

**Alternative considered:** Agent scrapes list pages live each cycle → rejected (slow, duplicate work, rate-limit risk).

### 2. Instrument type and ticker cache on `indices`

Each row in `indices` gains:

| Column | Type | Notes |
|--------|------|-------|
| `index_type` | `IndexType` enum | `COMPANY` or `ETF` — required, default `COMPANY` on migration |
| `boursorama_ticker` | str(32), nullable | e.g. `1rPAI` (action), `1rTPUST` (tracker) |

| Source | When |
|--------|------|
| User | `index_type` + optional `boursorama_ticker` on index create (API + `CreateIndexTool`) |
| Agent | `BoursoramaIndexResolver` auto-persist on first HTTP resolution |
| Agent (rare) | `UpdateIndexBoursoramaTool` — **manual override / correction only** |

**Resolution order** (DB-first — search at most once per index in steady state):

```
resolve(index_id | isin)
      │
      ├─ indices.boursorama_ticker IS NOT NULL → return ticker + canonical URLs
      │
      └─ NULL → SearchBoursoramaTool HTTP lookup (by isin or name)
                → UpdateIndexBoursoramaTool persists ticker on indices row
                → return ticker + URLs
```

Implemented as `BoursoramaIndexResolver` service shared by `SearchBoursoramaTool` and subagent workflows. Agents MUST prefer `get_index` / portfolio positions (which expose `boursorama_ticker`) before calling live search.

**Rationale:** Avoids repeated Bourso HTTP calls every market cycle for the same portfolio lines.

### 3. Replace Google search with `SearchBoursoramaTool`

User flow described: Google `"Air liquide boursorama"` → cours page.

**Decision:** `SearchBoursoramaTool` returns **type-aware** canonical URLs from `indices.index_type`:

**COMPANY** (`index_type=COMPANY`):

- `quote_url` = `https://www.boursorama.com/cours/{ticker}/`
- `news_url` = `https://www.boursorama.com/cours/actualites/{ticker}/`
- `key_figures_url` = `https://www.boursorama.com/cours/societe/chiffres-cles/{ticker}/`
- `composition_url` = null

**ETF** (`index_type=ETF`) — trackers live on BoursoBank host, **no per-ETF news page**:

- `quote_url` = `https://bourse.boursobank.com/bourse/trackers/cours/{ticker}/`
- `composition_url` = `https://bourse.boursobank.com/bourse/trackers/cours/composition/{ticker}/`
- `news_url` = null
- `key_figures_url` = null

ETF news strategy: `get_financials_news` (MARKETS, FINANCE, calendriers) + optional `get_data_from_url` on global hub `/bourse/actualites/`, then `get_etf_composition` to identify top holdings → `search_boursorama` on underlying **COMPANY** lines for targeted news.

**Rationale:** No Google API key, no CAPTCHA surface, stays within whitelist, deterministic for tests.

**Alternative considered:** Let agent use `GetDataFromUrlTool` on Google result URLs → rejected (SSRF/whitelist blocks non-Boursorama domains).

### 4. Ingest sources and schedule

| Job | Cron (Europe/Paris) | URLs | `NewsCategory` |
|-----|---------------------|------|----------------|
| `news.ingest.daily` | `0 7 * * *` | `/actualites/calendriers/`, `.../societes-cotees`, `.../macroeconomique`, `.../dividendes` | `CALENDAR_*` variants |
| `news.ingest.session` | EU POST_OPEN, mid PERIODIC, CLOSE (reuse `MarketSession` times) | `/actualites/marches/`, `/actualites/finances/` | `MARKETS`, `FINANCE` |

Session ingest fires **three times for EU only** in v1 (Boursorama is FR-centric). Timings align with existing phases:

- POST_OPEN → 09:20
- PERIODIC (mid) → 13:20 (first mid-session slot)
- CLOSE → 17:30

Ingest handlers run **without** `AgentRunner` — pure I/O + DB upsert.

### 5. DB model: `news_items`

```text
news_items
├── id (UUID PK)
├── source (NewsSource — BOURSORAMA)
├── category (NewsCategory)
├── title (str, NOT NULL)
├── source_url (str, UNIQUE, NOT NULL)  ← upsert key
├── summary (str, nullable)               ← list-page teaser
├── content_markdown (str, nullable)      ← filled on agent article persist (default persist=true)
├── content_embedding (vector(384))       ← computed on every upsert (title + summary + markdown)
├── boursorama_ticker (str, nullable)     ← e.g. 1rPAI when known
├── published_at (timestamptz, nullable)
├── fetched_at (timestamptz, NOT NULL)
└── ingest_run_id (UUID, nullable)        ← correlate batch
```

No `user_id` — news is global per deployment (single-user v1).

Enums in `nam_db.enums`:

- `NewsSource`: `BOURSORAMA`
- `NewsCategory`: `CALENDAR_GENERAL`, `CALENDAR_LISTED_COMPANIES`, `CALENDAR_MACRO`, `CALENDAR_DIVIDENDS`, `MARKETS`, `FINANCE`, `COMPANY_NEWS`

### 6. Scraper stack

```
agentic/nam_agentic/tools/services/boursorama/
├── client.py              # httpx AsyncClient, User-Agent, timeout, rate limit
├── list_parser.py         # ingest feed list pages (calendriers, marchés, finances)
├── company_news_parser.py # /cours/actualites/{ticker}/ → structured headlines (COMPANY only)
├── etf_composition_parser.py # tracker composition page → holdings list
├── search.py              # name/ISIN → ticker + type-aware URLs
├── page_formatter.py      # full articles + key figures: trafilatura → LLM
├── page_reader.py           # routes URL pattern → parser or formatter
└── ingest.py              # orchestrates list fetch + upsert
```

- **Ingest feed list pages (cron):** `list_parser.py` — structured only, no LLM
- **Company news index** (`/cours/actualites/{ticker}/`): `company_news_parser.py` — extract each row: `title`, `summary` (teaser), `article_url` ("lire la suite"), `published_at`, `attribution` — **no LLM**
- **Full article URL** (from `article_url`): `PageContentFormatter` — trafilatura → LLM (see §6.1)
- **Key figures URL:** `PageContentFormatter` with `page_hint=company_key_figures`
- **HTTP discipline:** shared `BoursoramaHttpClient` — browser-like headers, sequential-only, random jitter 1.5–4s between requests, per-minute/hour caps (see §6.2)

**Alternative considered:** Crawl4AI/Playwright → rejected for v1 weight/complexity; revisit if list pages require JS rendering.

### 6.1 `GetDataFromUrlTool` — two response modes (route by URL)

`page_reader.py` inspects the URL and picks the handler:

```
GET url
   │
   ├─ /cours/actualites/{ticker}/     → company_news_parser (COMPANY only)
   ├─ /bourse/actualites/            → list_parser (global hub — headlines + teasers)
   ├─ article URL (lire la suite)    → PageContentFormatter (trafilatura → LLM)
   ├─ /cours/societe/chiffres-cles/   → PageContentFormatter (COMPANY only)
   └─ other whitelisted paths         → PageContentFormatter (generic)

ETF composition is NOT handled by get_data_from_url — use GetEtfCompositionTool.
```

**Mode A — `content_type=news_index`** (company news listing)

Boursorama renders each item as: headline + teaser paragraph + "lire la suite" link. Parser MUST capture **all items** on the page:

```python
CompanyNewsHeadline:
  title: str
  summary: str          # teaser / first lines
  article_url: str      # absolute URL from "lire la suite"
  published_at: datetime | None
  attribution: str | None   # e.g. "Zonebourse", "Boursorama avec AFP"
```

Agent workflow: scan `headlines[]` → call `get_data_from_url(article_url)` **only** for items worth deepening.

**Mode B — `content_type=article`** (full read)

```
httpx → trafilatura → LLM → markdown
```

Used when agent follows a specific `article_url`. LLM structures the full article body for analysis.

**LLM prompt contract** (Mode B only):

- Input: `url`, `page_hint` (`article`, `company_key_figures`, `generic`), trafilatura output (truncated)
- For `company_key_figures`: preserve metrics as table/bullets
- Guards: empty trafilatura → error; `news_format_max_chars`; `news_format_llm_enabled` fallback

**Rationale:** Company news index is a **list with teasers** — structured parse is deterministic and gives the agent explicit `article_url` per item to choose deep reads. Dumping the index through trafilatura+LLM loses the per-article links and wastes tokens.

### 6.2 BoursoramaHttpClient — anti-spam / browser simulation

All Bourso traffic (cron ingest + tools) shares **one** client instance with:

```text
BoursoramaHttpClient (singleton)
├── browser-like headers (UA Chrome macOS, Accept-Language fr-FR, etc.)
├── asyncio.Semaphore(1)          # jamais 2 requêtes en parallèle
├── jitter: sleep(random.uniform(min, max)) before each GET
├── rolling window: max 12 req/min, 120 req/hour
└── redirect hook: allow only www.boursorama.com | bourse.boursobank.com
```

**No burst patterns:**

| Context | Max HTTP calls | Pattern |
|---------|----------------|---------|
| `news.ingest.daily` | 4 URLs | sequential + jitter |
| `news.ingest.session` | 2 URLs | sequential + jitter |
| `get_data_from_url` (index) | 1 | parse only, no prefetch articles |
| `get_data_from_url` (article) | 1 | trafilatura → LLM |
| Agent analysis task | ≤ 3 article deep-reads | prompt-enforced, 1 tool call = 1 URL |

On budget exceeded → `BoursoramaRateLimitError`, log warning, agent falls back to cached `news_items` / index teasers.

**Rationale:** Personal-use scraping still needs polite traffic — random jitter avoids robotic fixed-interval patterns; sequential fetch prevents "50 URLs d'un coup" even if the agent misbehaves.

### 7. Agent tools

| Tool | LLM input | Behavior |
|------|-----------|----------|
| `GetFinancialsNewsTool` | optional filters | SQL on `news_items` — primary news source for macro + ETF context |
| `GetDataFromUrlTool` | `url` | Route by URL pattern; COMPANY news index / global hub / articles / key figures |
| `SearchBoursoramaTool` | `query`, `isin`, or `index_id` | DB-first; type-aware URLs; auto-persist ticker |
| `GetEtfCompositionTool` | `index_id` or `boursorama_ticker` | ETF only — parse composition page, return holdings + weights |
| `UpdateIndexBoursoramaTool` | `index_id`, `boursorama_ticker` | Manual override only |

### 7.1 ETF vs COMPANY workflows

```
COMPANY (e.g. Air Liquide, index_type=COMPANY)
─────────────────────────────────────────────
get_index → boursorama_ticker?
search_boursorama(index_id) if missing
get_data_from_url(news_url)        → headlines[]
get_data_from_url(key_figures_url) → metrics
get_data_from_url(article_url)     → deep read (≤3)

ETF (e.g. Amundi MSCI World, index_type=ETF)
────────────────────────────────────────────
get_financials_news(MARKETS|FINANCE|CALENDAR_*)
get_data_from_url(/bourse/actualites/)  → global hub headlines (optional)
get_etf_composition(index_id)             → top holdings
for top holdings (COMPANY): search + news  → underlying exposure news
NO fetch of /cours/actualites/{etf_ticker}/ — page does not exist
```

### 7.2 Tool docstrings (LLM-facing descriptions)

LangChain exposes each `@tool` docstring as the **tool description** in the model's tool-calling interface — there is no `get_tools` meta-tool. Docstrings MUST be enriched (multi-line) so agents know **when / when-not / what-returns** without relying only on markdown prompts.

**Template** (all tools — existing basics + new market):

```python
"""<One-line imperative summary>.

Use when: <concrete trigger situations>.
Do not use when: <anti-patterns or wrong instrument type>.
Returns: <output shape in plain language>.
"""
```

**Examples:**

```python
# get_financials_news
"""Read cached Boursorama news and calendars from PostgreSQL.

Use when: macro brief, market headlines, or ETF context (no per-ETF news page).
Do not use when: you need a full article body — use get_data_from_url on article_url instead.
Returns: list of news items (title, summary, category, dates) newest first.
"""

# get_etf_composition
"""Fetch ETF tracker composition (holdings and weights) from BoursoBank.

Use when: index_type is ETF and you need underlying exposure before company news.
Do not use when: index_type is COMPANY — use search_boursorama + company news URLs.
Returns: holdings list with name, weight_pct, optional isin/ticker.
"""
```

Prompt markdown §5 ("TOOLS AT YOUR DISPOSAL") stays as workflow glue; docstrings are the **source of truth** for per-tool semantics.

### 7.3 Subagent tool wiring (extends basics-tools gap)

Subagents today only have `create_analysis` + `search_past_analyses`. This change adds:

| Subagent | Additional tools |
|----------|------------------|
| **Macro Strategist** | `get_financials_news`, `get_data_from_url` (global hub + articles) |
| **Sector Analyst** | above + `search_boursorama`, `update_index_boursorama`, `get_index`, `get_portfolio_positions` |
| **ETF Quant** | Sector set + `get_etf_composition` |
| **Portfolio Manager** | unchanged (no URL/search tools) |

Schemas live in `nam_agentic/tools/schemas/market.py`.

### 8. Event bus extension

New event types in `nam_agentic/schemas/events.py`:

| Type | Payload | Handler |
|------|---------|---------|
| `news.ingest.daily` | `{}` | `_on_news_ingest_daily` |
| `news.ingest.session` | `{market: Market}` | `_on_news_ingest_session` |

Scheduler callback enqueues events same as `market.session` (BackgroundTasks or internal dispatch).

### 9. ToolRegistry and subagent wiring

- `ToolRegistry.all_tools()` adds five market tools (see §7)
- Subagent assignment per §7.2
- PM does **not** get URL/search/ETF tools
- Subagent prompts: remove "planned (not available)"; document COMPANY vs ETF workflows

### 10. Security

- Allowed hosts: `www.boursorama.com`, `bourse.boursobank.com`
- Allowed path prefixes: `/bourse/`, `/cours/`
- Reject company-news URLs when `index_type=ETF` at tool level (`GetEtfCompositionTool`, `SearchBoursoramaTool` output)
- Block private IPs, redirects to non-whitelisted hosts (httpx `follow_redirects` with hook)
- No auth cookies / logged-in BoursoBank scraping

## Risks / Trade-offs

- **[Risk] Boursorama HTML layout changes** → Mitigation: fixture-based parser tests; ingest logs parse counts; alert on zero items
- **[Risk] ToS / blocking** → Mitigation: browser-like headers, random jitter, sequential fetch, per-minute/hour caps, max 3 deep article reads per agent task; no parallel crawl
- **[Risk] Calendar rows are not full articles** → Mitigation: `summary` from list; agent uses `GetDataFromUrlTool` for detail
- **[Risk] Search endpoint changes** → Mitigation: isolate `search.py`; fallback to `ListIndicesTool` name match
- **[Risk] ETF has no company news page** → Mitigation: `index_type` gate + composition → underlying COMPANY news loop
- **[Risk] Two Bourso hosts (boursorama vs boursobank)** → Mitigation: explicit host whitelist; type-aware URL builder in resolver
- **[Trade-off] News embeddings** → title+summary on cron, full body when persisted; semantic recall via `semantic_query`
- **[Trade-off] EU-only session ingest** → US/Asia cycles read stale MARKETS/FINANCE until next EU window; acceptable for FR portfolio focus
- **[Risk] LLM formatting adds latency per URL fetch** → Mitigation: only on `GetDataFromUrlTool` (on-demand); truncate input; `news_format_llm_enabled=false` fallback; mock in tests

## Migration Plan

1. Alembic migration: `news_items` + enums
2. Deploy agentic with ingest jobs (empty table OK)
3. Manual trigger: `POST /events` with `news.ingest.daily` to backfill
4. Enable subagent tools in registry + prompts
5. Rollback: drop migration; disable cron jobs; agents fall back to RAG-only (current behavior)

## Open Questions

- Whether mid-session ingest should run on **every** PERIODIC (2h) or only the **first mid** slot (13:20) — **default: first mid only** to limit scrape volume; adjustable via settings.
- Optional `persist=True` on `GetDataFromUrlTool` for company pages — **default: true** for article deep-reads; upserts `content_markdown` + embedding by `source_url`.
