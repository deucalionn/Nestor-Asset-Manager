## ADDED Requirements

### Requirement: uv workspace root
The repository MUST use a uv workspace at the root with `packages/db`, `api`, and `agentic` as workspace members.

#### Scenario: Workspace members resolve locally
- **WHEN** `uv sync` is run from the repository root
- **THEN** all three packages (`nam-db`, `nam-api`, `nam-agentic`) are installed in editable mode
- **AND** inter-package path dependencies resolve without publishing to PyPI

### Requirement: Python version constraint
The workspace MUST target Python ≥ 3.12.

#### Scenario: Version enforcement
- **WHEN** a developer runs `uv sync` with Python 3.11
- **THEN** uv reports a version mismatch error

### Requirement: Package naming convention
Each workspace member MUST use a `pyproject.toml` with a distinct distribution name: `nam-db`, `nam-api`, `nam-agentic`.

#### Scenario: Importable package names
- **WHEN** packages are installed
- **THEN** `import nam_db`, `import nam_api`, and `import nam_agentic` succeed

### Requirement: Dependency direction
Package dependencies MUST follow the directed graph: `nam-db` ← `nam-agentic` ← `nam-api`. `nam-db` MUST NOT depend on `nam-api` or `nam-agentic`.

#### Scenario: No circular dependencies
- **WHEN** `uv tree` is run from the root
- **THEN** no circular dependency between workspace packages is reported

### Requirement: Root dev dependencies
The root `pyproject.toml` MUST declare shared dev tools (e.g. `ruff`, `pytest`, `mypy`) available to all packages.

#### Scenario: Shared linting
- **WHEN** `uv run ruff check .` is run from root
- **THEN** all three packages are linted
