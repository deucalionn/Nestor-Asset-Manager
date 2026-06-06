# Tasks — analysis & recommendation schema

## 1. Enums & models (nam-db)

- [x] 1.1 Add `AnalysisTrigger` to `nam_db/enums.py`
- [x] 1.2 Implement `Analysis` ORM model (`title`, nullable `index_id`, `content`, `content_embedding`, `trigger`, relationships)
- [x] 1.3 Implement `Recommendation` ORM model (no `analysis_id` column)
- [x] 1.4 Implement `recommendation_analyses` association table / relationship helpers
- [x] 1.5 Update `nam_db/models/__init__.py` exports (`Analysis`, `Recommendation`)
- [x] 1.6 Add `User.analyses` and `User.recommendations` relationships

## 2. Alembic migration

- [x] 2.1 Create revision `analysis_recommendation` (depends on `portfolio_core`)
- [x] 2.2 Create PostgreSQL enums: `agent_enum`, `recommendation_type_enum`, `recommendation_status_enum`, `analysis_trigger_enum`
- [x] 2.3 Create tables `analyses`, `recommendations`, `recommendation_analyses` with FKs and indexes (HNSW on embedding)
- [x] 2.4 Verify `just migrate` on fresh and existing DB

## 3. API schemas & services

- [x] 3.1 Add `nam_api/schemas/analysis.py` and `nam_api/schemas/recommendation.py`
- [x] 3.2 Implement `AnalysisService` (list, get, filter by `index_id`)
- [x] 3.3 Implement `RecommendationService` (list, get with analyses, patch status/comment, transition rules)

## 4. API routes

- [x] 4.1 Add router: `GET /analyses`, `GET /analyses/{id}`
- [x] 4.2 Add router: `GET /recommendations`, `GET /recommendations/{id}`, `PATCH /recommendations/{id}`
- [x] 4.3 Register routers in `nam_api/main.py`

## 5. Tests

- [x] 5.1 Add factories/fixtures for Analysis and Recommendation in `api/tests/factories.py`
- [x] 5.2 API tests: analysis list/detail, recommendation list/detail
- [x] 5.3 API tests: apply, reject, 409 on double-resolve
- [x] 5.4 `just test` green

## 6. Documentation

- [x] 6.1 Update `openspec.md` §4.1 ERD and §4.3.5–4.3.6 (junction table, new columns, drop `analysis_id`)
