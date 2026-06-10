## ADDED Requirements

### Requirement: ChatThread model
`packages/db` MUST define a `ChatThread` SQLAlchemy model mapped to table `chat_threads`:

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK — same value as LangGraph `thread_id` |
| `user_id` | UUID | FK → `users.id`, NOT NULL, indexed |
| `title` | str | NOT NULL, max 120 chars |
| `created_at` | timestamptz | NOT NULL, server default |
| `updated_at` | timestamptz | NOT NULL, auto-update on write |

The model MUST NOT use French column names.

#### Scenario: Thread row created on first message
- **WHEN** a chat stream completes for a new UUID `thread_id`
- **THEN** a `chat_threads` row exists with `id=thread_id` and `user_id` set to the active user
- **AND** `title` is derived from the first user message (truncated) if not already set

#### Scenario: Market cron threads excluded
- **WHEN** a `thread_id` starts with `market:`
- **THEN** no `chat_threads` row is created for that id

### Requirement: Alembic migration for chat_threads
A single Alembic revision MUST create `chat_threads` with the constraints above.

#### Scenario: Migration applies cleanly
- **WHEN** `alembic upgrade head` runs on a fresh database
- **THEN** table `chat_threads` exists with FK to `users`
