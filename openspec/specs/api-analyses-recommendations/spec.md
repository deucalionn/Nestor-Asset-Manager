## Requirements

### Requirement: Analysis Pydantic schemas
The API MUST define in `nam_api/schemas/analysis.py`:

- `AnalysisRead`: `id`, `user_id`, `agent`, `index_id`, `title`, `content`, `trigger`, `created_at` — **excludes** `content_embedding` from HTTP responses
- `AnalysisListItem`: same fields as read (or alias) for list views

Enums MUST be imported from `nam_db.enums`.

#### Scenario: Response excludes embedding
- **WHEN** `GET /analyses/{id}` succeeds
- **THEN** the JSON body does not include `content_embedding`

### Requirement: Recommendation Pydantic schemas
The API MUST define in `nam_api/schemas/recommendation.py`:

- `RecommendationRead`: all persisted fields plus nested `analyses: list[AnalysisListItem]` (or IDs + titles)
- `RecommendationUpdate`: `status` (`RecommendationStatus`; APPLIED/REJECTED only — validate in service layer), optional `user_comment`

#### Scenario: Detail includes linked analyses
- **WHEN** `GET /recommendations/{id}` succeeds
- **THEN** the response includes the linked analyses (at minimum `id`, `title`, `agent`, `created_at`)

### Requirement: Analysis routes
Async routes MUST expose:

| Method | Route | Response |
|--------|-------|----------|
| GET | `/analyses` | `list[AnalysisListItem]` — optional query `index_id` |
| GET | `/analyses/{analysis_id}` | `AnalysisRead` |

#### Scenario: List analyses
- **WHEN** `GET /analyses` is called for a user with analyses
- **THEN** response status is 200
- **AND** results are ordered by `created_at` descending

#### Scenario: Filter by index
- **WHEN** `GET /analyses?index_id={uuid}` is called
- **THEN** only analyses with matching `index_id` are returned

#### Scenario: Unknown analysis
- **WHEN** `GET /analyses/{id}` references a non-existent row
- **THEN** response status is 404

### Requirement: Recommendation routes
Async routes MUST expose:

| Method | Route | Request | Response |
|--------|-------|---------|----------|
| GET | `/recommendations` | optional `status` filter | `list[RecommendationRead]` |
| GET | `/recommendations/{id}` | — | `RecommendationRead` |
| PATCH | `/recommendations/{id}` | `RecommendationUpdate` | `RecommendationRead` |

#### Scenario: List pending recommendations
- **WHEN** `GET /recommendations?status=PENDING` is called
- **THEN** only pending recommendations are returned

#### Scenario: Apply recommendation
- **WHEN** `PATCH /recommendations/{id}` sets `status=APPLIED`
- **THEN** response status is 200
- **AND** `resolved_at` is populated
- **AND** status remains `APPLIED` on subsequent GET

#### Scenario: Reject with comment
- **WHEN** `PATCH /recommendations/{id}` sets `status=REJECTED` with `user_comment`
- **THEN** the comment is persisted

#### Scenario: Invalid status transition
- **WHEN** `PATCH` attempts to change a recommendation already `APPLIED` or `REJECTED`
- **THEN** response status is 409

#### Scenario: Cannot set PENDING via PATCH
- **WHEN** `PATCH` sends `status=PENDING`
- **THEN** response status is 422

### Requirement: Service layer
`AnalysisService` and `RecommendationService` MUST use `AsyncSession`, return Pydantic read models, and load junction data for recommendation detail.

#### Scenario: Async handlers
- **WHEN** analysis/recommendation router modules are reviewed
- **THEN** every endpoint is `async def` and delegates to services

### Requirement: API tests
`api/tests/` MUST include tests for list/detail analyses, list/detail recommendations, apply/reject flows, and invalid transitions.

#### Scenario: Docker test run
- **WHEN** `just test` runs
- **THEN** analysis and recommendation API tests pass
