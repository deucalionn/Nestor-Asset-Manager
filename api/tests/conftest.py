import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from nam_api.dependencies import get_db_session
from nam_api.main import app
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://nam:nam@localhost:5432/nam_test"
)

TRUNCATE_TABLES = (
    "recommendation_analyses",
    "recommendations",
    "analyses",
    "positions",
    "transactions",
    "indices",
    "users",
)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


async def truncate_portfolio_tables(engine) -> None:
    table_list = ", ".join(TRUNCATE_TABLES)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    await truncate_portfolio_tables(engine)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
            await truncate_portfolio_tables(engine)
            await engine.dispose()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
