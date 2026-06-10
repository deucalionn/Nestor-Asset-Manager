## MODIFIED Requirements

### Requirement: CompositeBackend for agent filesystem
`DeepAgentFactory.build()` MUST pass a `CompositeBackend` to `create_deep_agent(backend=...)` with:

| Route prefix | Backend | Root |
|--------------|---------|------|
| `/shared/` | `FilesystemBackend` | `{agent_workspace_dir}/shared` |
| `/user/` | `FilesystemBackend` | `{agent_workspace_dir}/user` |
| (default) | `StateBackend` | thread-scoped (checkpointed) |

`FilesystemBackend` MUST use `virtual_mode=True` so agent paths stay under routed prefixes.

The same backend instance MUST be used by the main agent and all declarative subagents (Deep Agents default — no per-subagent backend override).

#### Scenario: Shared path resolves to volume directory
- **WHEN** the agent calls `write_file` with path `/shared/calendar/today.md`
- **THEN** content is written to `{agent_workspace_dir}/shared/calendar/today.md` on the host filesystem
- **AND** the path is not under the git repository source tree unless `agent_workspace_dir` explicitly points there

#### Scenario: User workspace path resolves to volume directory
- **WHEN** the agent calls `write_file` with path `/user/{user_id}/USER_GOALS.md`
- **THEN** content is written to `{agent_workspace_dir}/user/{user_id}/USER_GOALS.md`
- **AND** the file survives `nam-agentic` process restart when the volume is mounted

#### Scenario: Ephemeral paths stay in StateBackend
- **WHEN** the agent writes to `/notes/scratch.md` (no `/shared/` or `/user/` prefix)
- **THEN** content is stored in `StateBackend` only
- **AND** it is not persisted under `{agent_workspace_dir}/shared` or `user`

### Requirement: Agent workspace directory setting
`nam_agentic/settings.py` MUST expose `agent_workspace_dir: Path` (env `AGENT_WORKSPACE_DIR`, default `{repo_root}/data/agent_workspace`).

On agentic startup, `{agent_workspace_dir}/shared` and `{agent_workspace_dir}/user` MUST be created if missing (same lifecycle as existing workspace mkdir in `EventHandler`).

#### Scenario: Default workspace outside tracked content
- **WHEN** `AGENT_WORKSPACE_DIR` is unset
- **THEN** default resolves to `data/agent_workspace` at repo root
- **AND** that directory is listed in `.gitignore`

#### Scenario: User subdirectory created for onboarding
- **WHEN** `user.profile.created` is handled
- **THEN** `{agent_workspace_dir}/user/{user_id}/` exists or is created before the agent run
