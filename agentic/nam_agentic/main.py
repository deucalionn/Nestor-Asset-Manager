"""FastAPI entrypoint for nam-agentic — lifespan, scheduler, and HTTP routes."""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from nam_agentic.bootstrap import build_agent_runner, build_event_handler
from nam_agentic.checkpoint_url import to_psycopg_conn_string
from nam_agentic.routers import chat, events, health
from nam_agentic.runtime import AgentRuntime, set_runtime
from nam_agentic.scheduler.scheduler import register_market_jobs, register_news_ingest_jobs
from nam_agentic.schemas.events import AgentEvent
from nam_agentic.settings import settings

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def _wire_runtime(app: FastAPI, agent_runner, event_handler) -> None:
    set_runtime(AgentRuntime(agent_runner=agent_runner, event_handler=event_handler))
    app.state.agent_runner = agent_runner
    app.state.event_handler = event_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open Postgres checkpointer, bootstrap agent runtime, start market scheduler."""
    logging.basicConfig(level=logging.INFO)
    conn_string = to_psycopg_conn_string(settings.database_url)
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        agent_runner = build_agent_runner(checkpointer)
        event_handler = build_event_handler(agent_runner)
        _wire_runtime(app, agent_runner, event_handler)

        async def on_market_event(event: AgentEvent) -> None:
            await event_handler.handle(event)

        register_market_jobs(
            scheduler,
            on_market_event,
            timezone=settings.market_timezone,
        )
        register_news_ingest_jobs(
            scheduler,
            on_market_event,
            timezone=settings.market_timezone,
        )
        scheduler.start()
        logger.info(
            "nam-agentic started — agent ready, scheduler active (%s), workspace=%s",
            settings.market_timezone,
            settings.agent_workspace_dir,
        )
        yield
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nestor Asset Manager — Agent Runtime",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(events.router)
    app.include_router(chat.router)
    return app


app = create_app()
