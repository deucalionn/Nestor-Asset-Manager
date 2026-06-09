import pytest
from factories import IndexFactory
from nam_api.exceptions import ConflictError, NotFoundError
from nam_api.schemas.index import IndexCreate
from nam_api.services.index_service import IndexService
from nam_db.enums import IndexType
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def service() -> IndexService:
    return IndexService()


async def test_create_index(db_session: AsyncSession, service: IndexService) -> None:
    result = await service.create(
        db_session,
        IndexCreate(name="CAC 40", isin="FR0003500008", index_type=IndexType.COMPANY),
    )
    await db_session.commit()

    assert result.name == "CAC 40"
    assert result.isin == "FR0003500008"
    assert result.id is not None


async def test_list_indices(db_session: AsyncSession, service: IndexService) -> None:
    await IndexFactory.create(db_session, name="S&P 500", isin="US78378X1072")
    await IndexFactory.create(db_session, name="CAC 40", isin="FR0003500008")
    await db_session.commit()

    indices = await service.list(db_session)

    assert len(indices) == 2
    assert indices[0].name == "CAC 40"
    assert indices[1].name == "S&P 500"


async def test_get_index(db_session: AsyncSession, service: IndexService) -> None:
    index = await IndexFactory.create(db_session)
    await db_session.commit()

    result = await service.get(db_session, index.id)

    assert result.id == index.id
    assert result.isin == index.isin


async def test_get_index_not_found(db_session: AsyncSession, service: IndexService) -> None:
    from uuid import uuid4

    with pytest.raises(NotFoundError):
        await service.get(db_session, uuid4())


async def test_create_etf_index(db_session: AsyncSession, service: IndexService) -> None:
    result = await service.create(
        db_session,
        IndexCreate(
            name="Amundi MSCI World",
            isin="FR0010315770",
            index_type=IndexType.ETF,
            boursorama_ticker="1rTEWLD",
        ),
    )
    await db_session.commit()

    assert result.index_type == IndexType.ETF
    assert result.boursorama_ticker == "1rTEWLD"


async def test_create_index_with_yahoo_symbol(
    db_session: AsyncSession, service: IndexService
) -> None:
    result = await service.create(
        db_session,
        IndexCreate(
            name="Air Liquide",
            isin="FR0000120073",
            index_type=IndexType.COMPANY,
            yahoo_symbol="AI.PA",
        ),
    )
    await db_session.commit()

    assert result.yahoo_symbol == "AI.PA"


async def test_duplicate_isin(db_session: AsyncSession, service: IndexService) -> None:
    await service.create(
        db_session,
        IndexCreate(name="CAC 40", isin="FR0003500008", index_type=IndexType.COMPANY),
    )
    await db_session.commit()

    with pytest.raises(ConflictError):
        await service.create(
            db_session,
            IndexCreate(name="CAC 40 Copy", isin="FR0003500008", index_type=IndexType.COMPANY),
        )
