from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from nam_api.dependencies import get_db_session
from nam_api.main import app
from nam_db.tests_support import get_test_database_url, truncate_test_tables
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    await truncate_test_tables(engine)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
            await truncate_test_tables(engine)
            await engine.dispose()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
