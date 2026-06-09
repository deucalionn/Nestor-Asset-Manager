## ADDED Requirements

### Requirement: News ingest scheduler jobs
In addition to `market.session` cron jobs, `nam-agentic` lifespan MUST register:

1. **Daily news ingest** — `news.ingest.daily` at 07:00 Europe/Paris
2. **Session news ingest** — `news.ingest.session` at EU POST_OPEN (09:20), first mid PERIODIC (13:20), and CLOSE (17:30) Europe/Paris

#### Scenario: News jobs registered at startup
- **WHEN** `nam-agentic` lifespan enters
- **THEN** APScheduler has jobs for `news.ingest.daily` and three EU `news.ingest.session` triggers
- **AND** jobs are removed on lifespan shutdown

### Requirement: News ingest event dispatch
`POST /events` MUST accept `news.ingest.daily` and `news.ingest.session` and return 202 before async processing.

#### Scenario: Session ingest event accepted
- **WHEN** `POST /events` is sent with `type=news.ingest.session` and payload `{market: "EU"}`
- **THEN** the response status is 202
- **AND** `EventHandler` invokes the news ingest handler without `AgentRunner`
