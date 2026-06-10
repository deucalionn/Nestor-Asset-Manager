from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from nam_agentic.backends.shared import SHARED_ROUTE_PREFIX, USER_ROUTE_PREFIX, build_agent_backend
from nam_agentic.context import NamRuntimeContext
from nam_agentic.enums import Market, MarketPhase
from nam_agentic.schemas.events import AgentEvent, EventType
from nam_agentic.services.event_handler import (
    ONBOARDING_SEED_MESSAGE,
    PROFILE_REFRESH_SEED_MESSAGE,
    EventHandler,
    market_session_seed_message,
    market_thread_id,
)


@pytest.mark.asyncio
async def test_build_agent_backend_writes_shared_path(tmp_path: Path) -> None:
    backend = build_agent_backend(workspace_dir=tmp_path)
    result = backend.write(f"{SHARED_ROUTE_PREFIX}calendar/today.md", "# test\n")
    assert result.error is None

    read = backend.read(f"{SHARED_ROUTE_PREFIX}calendar/today.md")
    assert read.error is None
    assert read.file_data is not None
    assert "# test" in read.file_data["content"]

    assert (tmp_path / "shared" / "calendar" / "today.md").is_file()


@pytest.mark.asyncio
async def test_build_agent_backend_writes_user_path(tmp_path: Path) -> None:
    backend = build_agent_backend(workspace_dir=tmp_path)
    user_id = uuid4()
    path = f"{USER_ROUTE_PREFIX}{user_id}/USER_GOALS.md"
    result = backend.write(path, "# goals\n")
    assert result.error is None

    read = backend.read(path)
    assert read.error is None
    assert read.file_data is not None
    assert "# goals" in read.file_data["content"]
    assert (tmp_path / "user" / str(user_id) / "USER_GOALS.md").is_file()


@pytest.mark.asyncio
async def test_market_session_invokes_agent_runner(tmp_path: Path) -> None:
    runner = AsyncMock()
    runner.invoke = AsyncMock(return_value={"messages": []})
    handler = EventHandler(workspace_dir=tmp_path, agent_runner=runner)

    event = AgentEvent(
        type=EventType.MARKET_SESSION,
        payload={"market": Market.EU.value, "phase": MarketPhase.PRE_OPEN.value},
    )
    await handler.handle(event)

    runner.invoke.assert_awaited_once()
    message, = runner.invoke.await_args.args
    assert Market.EU.value in message
    assert MarketPhase.PRE_OPEN.value in message
    context = runner.invoke.await_args.kwargs["context"]
    assert isinstance(context, NamRuntimeContext)
    assert context.market == Market.EU
    assert context.phase == MarketPhase.PRE_OPEN
    assert context.thread_id == market_thread_id(Market.EU, MarketPhase.PRE_OPEN)


@pytest.mark.asyncio
async def test_profile_created_invokes_onboarding_seed(tmp_path: Path) -> None:
    runner = AsyncMock()
    runner.invoke = AsyncMock(return_value={"messages": []})
    handler = EventHandler(workspace_dir=tmp_path, agent_runner=runner)
    user_id = uuid4()

    await handler.handle(
        AgentEvent(type=EventType.USER_PROFILE_CREATED, user_id=user_id),
    )

    runner.invoke.assert_awaited_once()
    message = runner.invoke.await_args.args[0]
    assert "USER_GOALS.md" in message
    assert message == ONBOARDING_SEED_MESSAGE.format(user_id=user_id)
    assert (tmp_path / "user" / str(user_id)).is_dir()


@pytest.mark.asyncio
async def test_profile_updated_invokes_refresh_seed(tmp_path: Path) -> None:
    runner = AsyncMock()
    runner.invoke = AsyncMock(return_value={"messages": []})
    handler = EventHandler(workspace_dir=tmp_path, agent_runner=runner)
    user_id = uuid4()

    await handler.handle(
        AgentEvent(type=EventType.USER_PROFILE_UPDATED, user_id=user_id),
    )

    runner.invoke.assert_awaited_once()
    message = runner.invoke.await_args.args[0]
    assert message == PROFILE_REFRESH_SEED_MESSAGE.format(user_id=user_id)


@pytest.mark.asyncio
async def test_news_ingest_session_does_not_invoke_agent_runner(tmp_path: Path) -> None:
    runner = AsyncMock()
    runner.invoke = AsyncMock()
    handler = EventHandler(workspace_dir=tmp_path, agent_runner=runner)
    handler._news_ingest = AsyncMock()  # noqa: SLF001
    run_id = "00000000-0000-0000-0000-000000000001"
    handler._news_ingest.ingest_session = AsyncMock(return_value=run_id)

    event = AgentEvent(
        type=EventType.NEWS_INGEST_SESSION,
        payload={"market": Market.EU.value},
    )
    await handler.handle(event)

    runner.invoke.assert_not_awaited()
    handler._news_ingest.ingest_session.assert_awaited_once()  # noqa: SLF001


def test_market_session_seed_message() -> None:
    message = market_session_seed_message(Market.EU, MarketPhase.PRE_OPEN)
    assert "EU" in message
    assert "PRE_OPEN" in message


@pytest.mark.asyncio
async def test_event_handler_creates_shared_workspace(tmp_path: Path) -> None:
    handler = EventHandler(workspace_dir=tmp_path, agent_runner=None)
    await handler.handle(AgentEvent(type=EventType.USER_PROFILE_CREATED))
    assert (tmp_path / "shared").is_dir()
