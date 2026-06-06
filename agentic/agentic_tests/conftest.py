from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from nam_db.enums import AgentRole, AnalysisTrigger, Strategy
from nam_db.models.analysis import Analysis
from nam_db.models.index import Index
from nam_db.models.position import Position
from nam_db.models.user import User
from nam_db.tests_support import get_test_database_url, truncate_test_tables
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from support.helpers import EMBEDDING_DIM, MockEmbeddingService


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_engine():
    engine = create_async_engine(get_test_database_url())
    await truncate_test_tables(engine)
    yield engine
    await truncate_test_tables(engine)
    await engine.dispose()


@pytest.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


@pytest.fixture
def mock_embedding() -> MockEmbeddingService:
    return MockEmbeddingService()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        firstname="Jane",
        date_of_birth=date(1990, 6, 15),
        strategy=Strategy.GROWTH,
        goals="Retire early",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_index(db_session: AsyncSession) -> Index:
    index = Index(name="Alphabet Inc (Google)", isin="US02079K3059")
    db_session.add(index)
    await db_session.commit()
    await db_session.refresh(index)
    return index


@pytest.fixture
async def test_position(
    db_session: AsyncSession, test_user: User, test_index: Index
) -> Position:
    position = Position(
        user_id=test_user.id,
        index_id=test_index.id,
        quantity=Decimal("10"),
        average_cost=Decimal("100"),
        last_update=datetime.now(UTC),
    )
    db_session.add(position)
    await db_session.commit()
    await db_session.refresh(position)
    return position


@pytest.fixture
async def test_analysis(db_session: AsyncSession, test_user: User) -> Analysis:
    analysis = Analysis(
        user_id=test_user.id,
        agent=AgentRole.MACRO_STRATEGIST,
        title="Macro outlook",
        content="A" * 100,
        content_embedding=[1.0] + [0.0] * (EMBEDDING_DIM - 1),
        trigger=AnalysisTrigger.MARKET_SESSION,
    )
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)
    return analysis
