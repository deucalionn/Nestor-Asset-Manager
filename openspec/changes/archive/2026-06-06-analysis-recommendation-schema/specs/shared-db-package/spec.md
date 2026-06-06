## MODIFIED Requirements

### Requirement: Model module stubs
Implemented ORM models MUST exist for all planned entities. Portfolio entities (`user`, `index`, `transaction`, `position`) and agent-memory entities (`analysis`, `recommendation`) MUST be fully mapped — not empty stubs.

#### Scenario: Model package structure
- **WHEN** `from nam_db.models import Analysis, Recommendation` is executed
- **THEN** both classes are SQLAlchemy mapped models with table definitions

#### Scenario: Alembic discovery
- **WHEN** `alembic revision --autogenerate` runs after model changes
- **THEN** `Analysis` and `Recommendation` are included in metadata

## ADDED Requirements

### Requirement: AnalysisTrigger in shared enums
`nam_db/enums.py` MUST export `AnalysisTrigger` alongside existing domain enums.

#### Scenario: Cross-package import
- **WHEN** API or agentic code needs an analysis trigger value
- **THEN** it imports `AnalysisTrigger` from `nam_db.enums`
