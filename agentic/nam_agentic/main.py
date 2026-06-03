import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from nam_agentic.dependencies import event_handler
from nam_agentic.routers import events, health
from nam_agentic.scheduler.scheduler import register_market_jobs
from nam_agentic.schemas.events import AgentEvent
from nam_agentic.settings import settings

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(level=logging.INFO)

    async def on_market_event(event: AgentEvent) -> None:
        await event_handler.handle(event)

    register_market_jobs(
        scheduler,
        on_market_event,
        timezone=settings.market_timezone,
    )
    scheduler.start()
    logger.info(
        "nam-agentic started — scheduler active (%s), workspace=%s",
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
    return app


app = create_app()
