from uuid import UUID

from nam_db.models.index import Index
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.exceptions import ConflictError, NotFoundError
from nam_api.schemas.index import IndexCreate, IndexRead


class IndexService:
    async def create(self, session: AsyncSession, data: IndexCreate) -> IndexRead:
        index = Index(
            name=data.name,
            isin=data.isin,
            index_type=data.index_type,
            boursorama_ticker=data.boursorama_ticker,
            yahoo_symbol=data.yahoo_symbol,
        )
        session.add(index)
        try:
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            raise ConflictError("Index with this ISIN already exists") from exc
        return IndexRead.model_validate(index)

    async def get(self, session: AsyncSession, index_id: UUID) -> IndexRead:
        index = await session.get(Index, index_id)
        if index is None:
            raise NotFoundError("Index not found")
        return IndexRead.model_validate(index)

    async def list(self, session: AsyncSession) -> list[IndexRead]:
        result = await session.execute(select(Index).order_by(Index.name))
        return [IndexRead.model_validate(row) for row in result.scalars().all()]
