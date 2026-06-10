"""Volume-backed filesystem routes for the Deep Agents CompositeBackend."""

from pathlib import Path

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from nam_agentic.settings import settings

SHARED_ROUTE_PREFIX = "/shared/"
USER_ROUTE_PREFIX = "/user/"


def build_agent_backend(
    workspace_dir: Path | None = None,
) -> CompositeBackend:
    """Mount ``/shared/`` and ``/user/`` on the agent workspace volume."""
    root = workspace_dir or settings.agent_workspace_dir
    shared_root = root / "shared"
    user_root = root / "user"
    shared_root.mkdir(parents=True, exist_ok=True)
    user_root.mkdir(parents=True, exist_ok=True)
    return CompositeBackend(
        default=StateBackend(),
        routes={
            SHARED_ROUTE_PREFIX: FilesystemBackend(
                root_dir=shared_root,
                virtual_mode=True,
            ),
            USER_ROUTE_PREFIX: FilesystemBackend(
                root_dir=user_root,
                virtual_mode=True,
            ),
        },
    )
