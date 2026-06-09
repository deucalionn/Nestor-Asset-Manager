## MODIFIED Requirements

### Requirement: Boursorama list feed configuration
`nam-agentic` MUST define a static configuration mapping ingest jobs to source URLs and categories:

| Job | URLs (path suffix under `https://www.boursorama.com`) | Category |
|-----|------------------------------------------------------|----------|
| session | `/bourse/actualites/marches/` | `MARKETS` |
| session | `/bourse/actualites/finances/` | `FINANCE` |

Calendar URLs MUST live in `CALENDAR_FEEDS` (see `bourso-calendar-shared-file` spec) and MUST NOT be ingested into `news_items` by cron.

#### Scenario: Session job covers market and finance pages
- **WHEN** `news.ingest.session` runs successfully
- **THEN** both session URLs are fetched
- **AND** at least one `news_items` row per page is inserted or updated when the page contains entries

## REMOVED Requirements

### Requirement: Daily ingest schedule
**Reason**: Calendar data is fetched on demand by the Portfolio Manager and stored on the Deep Agent shared filesystem backend (`/shared/calendar/today.md`). Scheduled SQL ingest of calendar pages used the wrong parser and duplicated ephemeral data in PostgreSQL.

**Migration**: Calendar refresh happens inside `market.session` agent runs (`fetch_calendar_from_bourso` + PM `write_file`) — not via cron. Existing `CALENDAR_*` rows in `news_items` may be ignored or manually deleted; no automated backfill.

#### Scenario: Daily cron fires
- **WHEN** the clock reaches 07:00 Europe/Paris
- **THEN** no `news.ingest.daily` event is enqueued

### Requirement: Boursorama list feed configuration — daily calendar rows
**Reason**: Superseded by `CALENDAR_FEEDS` + agent fetch tool; calendar no longer ingested to SQL.

**Migration**: See daily ingest schedule removal above.

#### Scenario: Daily job covers four calendar pages
- **WHEN** any automated ingest job runs
- **THEN** calendar URLs are not fetched for `news_items` upsert

## ADDED Requirements

### Requirement: Calendar feeds excluded from NewsIngestService
`NewsIngestService.ingest_daily()` MUST be removed or MUST NOT be invoked by scheduler/events.

`NewsIngestService` MUST only ingest `SESSION_FEEDS` via `ingest_session()`.

#### Scenario: Ingest service has no daily batch
- **WHEN** reviewing `NewsIngestService` public methods used by `EventHandler`
- **THEN** only session ingest is wired
- **AND** no code path upserts calendar categories from cron

#### Scenario: Session ingest never invokes AgentRunner
- **WHEN** `news.ingest.session` is handled
- **THEN** `NewsIngestService.ingest_session()` runs
- **AND** `AgentRunner` is not invoked
