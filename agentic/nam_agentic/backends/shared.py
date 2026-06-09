from pathlib import Path

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from nam_agentic.settings import settings

SHARED_ROUTE_PREFIX = "/shared/"


def build_agent_backend(
    workspace_dir: Path | None = None,
) -> CompositeBackend:
    root = workspace_dir or settings.agent_workspace_dir
    shared_root = root / "shared"
    shared_root.mkdir(parents=True, exist_ok=True)
    return CompositeBackend(
        default=StateBackend(),
        routes={
            SHARED_ROUTE_PREFIX: FilesystemBackend(
                root_dir=shared_root,
                virtual_mode=True,
            ),
        },
    )
