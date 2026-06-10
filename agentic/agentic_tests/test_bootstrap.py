import os

import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from nam_agentic.bootstrap import build_agent_runner
from nam_agentic.checkpoint_url import to_psycopg_conn_string
from nam_agentic.settings import settings


def _checkpoint_database_url() -> str:
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]
    return str(settings.database_url)


@pytest.mark.anyio
async def test_build_agent_runner_compiles_graph() -> None:
    conn_string = to_psycopg_conn_string(_checkpoint_database_url())
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        runner = build_agent_runner(checkpointer)
    assert runner is not None
