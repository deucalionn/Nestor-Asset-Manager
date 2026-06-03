from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.dependencies import get_db_session, get_singleton_user_id
from nam_api.schemas.position import PositionRead
from nam_api.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate
from nam_api.services.position_service import PositionService
from nam_api.services.transaction_service import TransactionService

transactions_router = APIRouter(prefix="/transactions", tags=["transactions"])
positions_router = APIRouter(prefix="/positions", tags=["positions"])


def get_transaction_service() -> TransactionService:
    return TransactionService()


def get_position_service() -> PositionService:
    return PositionService()


@transactions_router.get("", response_model=list[TransactionRead])
async def list_transactions(
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: TransactionService = Depends(get_transaction_service),
) -> list[TransactionRead]:
    return await service.list_for_user(session, user_id)


@transactions_router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    body: TransactionCreate,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionRead:
    return await service.create(session, user_id, body)


@transactions_router.put("/{transaction_id}", response_model=TransactionRead)
async def update_transaction(
    transaction_id: UUID,
    body: TransactionUpdate,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionRead:
    return await service.update(session, user_id, transaction_id, body)


@transactions_router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: TransactionService = Depends(get_transaction_service),
) -> Response:
    await service.delete(session, user_id, transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@positions_router.get("", response_model=list[PositionRead])
async def list_positions(
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: PositionService = Depends(get_position_service),
) -> list[PositionRead]:
    return await service.list_for_user(session, user_id)
