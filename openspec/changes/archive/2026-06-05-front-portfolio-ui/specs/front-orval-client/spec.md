## ADDED Requirements

### Requirement: Orval generates client from nam-api OpenAPI

The front MUST configure Orval to fetch the OpenAPI schema from nam-api only and generate TypeScript types plus React Query hooks.

#### Scenario: Code generation from running API

- **WHEN** the developer runs `pnpm orval` with nam-api serving `GET /openapi.json`
- **THEN** generated files are written under `front/src/api/generated/`
- **AND** hooks exist for profile, indices, positions, and transactions endpoints

#### Scenario: API base URL from environment

- **WHEN** the front makes API requests in development
- **THEN** the base URL MUST come from `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`)
- **AND** no requests are sent to nam-agentic (`:8001`)

### Requirement: Generated hooks cover portfolio endpoints

The generated client MUST include operations for at minimum:

- `POST /setup`, `GET /profile`
- `GET /indices`, `POST /indices`
- `GET /positions`
- `POST /transactions`

#### Scenario: Type safety for UserCreate

- **WHEN** the onboarding form submits setup payload
- **THEN** the payload MUST be typed as `UserCreate` matching nam-api schema (firstname, date_of_birth, strategy, goals)

#### Scenario: Regeneration after API change

- **WHEN** nam-api Pydantic schemas change
- **THEN** running `pnpm orval` updates generated types without manual edits to hook signatures
