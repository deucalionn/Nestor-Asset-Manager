## ADDED Requirements

### Requirement: CompositeBackend for agent filesystem
`DeepAgentFactory.build()` MUST pass a `CompositeBackend` to `create_deep_agent(backend=...)` with:

| Route prefix | Backend | Root |
|--------------|---------|------|
| `/shared/` | `FilesystemBackend` | `{agent_workspace_dir}/shared` |
| (default) | `StateBackend` | ephemeral |

`FilesystemBackend` MUST use `virtual_mode=True` so agent paths stay under `/shared/`.

The same backend instance MUST be used by the main agent and all declarative subagents (Deep Agents default — no per-subagent backend override).

#### Scenario: Shared path resolves to volume directory
- **WHEN** the agent calls `write_file` with path `/shared/calendar/today.md`
- **THEN** content is written to `{agent_workspace_dir}/shared/calendar/today.md` on the host filesystem
- **AND** the path is not under the git repository source tree unless `agent_workspace_dir` explicitly points there

#### Scenario: Ephemeral paths stay in StateBackend
- **WHEN** the agent writes to `/notes/scratch.md` (no `/shared/` prefix)
- **THEN** content is stored in `StateBackend` only
- **AND** it is not persisted under `{agent_workspace_dir}/shared`

### Requirement: Agent workspace directory setting
`nam_agentic/settings.py` MUST expose `agent_workspace_dir: Path` (env `AGENT_WORKSPACE_DIR`, default `{repo_root}/data/agent_workspace`).

On agentic startup, `{agent_workspace_dir}/shared` MUST be created if missing (same lifecycle as existing workspace mkdir in `EventHandler`).

#### Scenario: Default workspace outside tracked content
- **WHEN** `AGENT_WORKSPACE_DIR` is unset
- **THEN** default resolves to `data/agent_workspace` at repo root
- **AND** that directory is listed in `.gitignore`

### Requirement: Runtime volume persistence
Deployment documentation (`.env.example` and dev infra when present) MUST document mounting `agent_workspace_dir` as a persistent Docker volume so `/shared/` files survive container restarts.

#### Scenario: Container restart retains calendar file
- **GIVEN** `/shared/calendar/today.md` was written before restart
- **WHEN** `nam-agentic` restarts with the same volume mount
- **THEN** `read_file("/shared/calendar/today.md")` returns the previous content

### Requirement: Native filesystem tools for shared reads
Agents MUST NOT receive a custom tool whose sole purpose is reading `/shared/calendar/today.md`.

Subagents MUST access shared calendar content exclusively via Deep Agents built-in filesystem tools (`read_file`, `grep`, `glob`) on the configured backend.

#### Scenario: No ReadCalendarTool in registry
- **WHEN** `ToolRegistry` and subagent `tools()` lists are reviewed
- **THEN** no tool named `read_calendar` or equivalent read-only calendar wrapper exists

#### Scenario: Subagent reads shared file natively
- **WHEN** a subagent needs today's calendar during a market session
- **THEN** it uses `read_file` with path `/shared/calendar/today.md`
- **AND** no SQL query to `news_items` is required for calendar context

### Requirement: Backend factory module
`nam_agentic/backends/` MUST expose a function (e.g. `build_agent_backend() -> CompositeBackend`) that encapsulates route configuration from settings — keeping `factory.py` thin.

#### Scenario: Factory delegates backend construction
- **WHEN** `DeepAgentFactory.build()` is called
- **THEN** it uses `build_agent_backend()` rather than inline backend construction
