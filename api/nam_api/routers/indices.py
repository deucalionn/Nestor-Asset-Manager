from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.dependencies import get_db_session
from nam_api.schemas.index import IndexCreate, IndexRead
from nam_api.services.index_service import IndexService

router = APIRouter(prefix="/indices", tags=["indices"])


def get_index_service() -> IndexService:
    return IndexService()


@router.get("", response_model=list[IndexRead])
async def list_indices(
    session: AsyncSession = Depends(get_db_session),
    service: IndexService = Depends(get_index_service),
) -> list[IndexRead]:
    return await service.list(session)


@router.post("", response_model=IndexRead, status_code=status.HTTP_201_CREATED)
async def create_index(
    body: IndexCreate,
    session: AsyncSession = Depends(get_db_session),
    service: IndexService = Depends(get_index_service),
) -> IndexRead:
    index = await service.create(session, body)
    await session.commit()
    return index


@router.get("/{index_id}", response_model=IndexRead)
async def get_index(
    index_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: IndexService = Depends(get_index_service),
) -> IndexRead:
    return await service.get(session, index_id)
