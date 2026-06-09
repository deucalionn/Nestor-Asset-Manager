## Requirements

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

### Requirement: No daily calendar cron
Calendar data is fetched on demand by the Portfolio Manager and stored on the Deep Agent shared filesystem backend (`/shared/calendar/today.md`). Scheduled SQL ingest of calendar pages MUST NOT run.

Existing `CALENDAR_*` rows in `news_items` may be ignored or manually deleted; no automated backfill.

#### Scenario: Daily cron does not fire
- **WHEN** the clock reaches 07:00 Europe/Paris
- **THEN** no `news.ingest.daily` event is enqueued

#### Scenario: Automated ingest excludes calendar URLs
- **WHEN** any automated ingest job runs
- **THEN** calendar URLs are not fetched for `news_items` upsert
