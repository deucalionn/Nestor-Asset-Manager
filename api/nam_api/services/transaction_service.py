from uuid import UUID

from nam_db.models.index import Index
from nam_db.models.transaction import Transaction
from nam_db.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.exceptions import InsufficientQuantityError, NotFoundError
from nam_api.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate
from nam_api.services.position_service import PositionService


class TransactionService:
    def __init__(self, position_service: PositionService | None = None) -> None:
        self._position_service = position_service or PositionService()

    async def list_for_user(
        self, session: AsyncSession, user_id: UUID
    ) -> list[TransactionRead]:
        await self._ensure_user_exists(session, user_id)
        result = await session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.date, Transaction.created_at)
        )
        return [TransactionRead.model_validate(row) for row in result.scalars().all()]

    async def create(
        self, session: AsyncSession, user_id: UUID, data: TransactionCreate
    ) -> TransactionRead:
        await self._ensure_user_exists(session, user_id)
        await self._ensure_index_exists(session, data.index_id)

        transaction = Transaction(
            user_id=user_id,
            index_id=data.index_id,
            type=data.type,
            price=data.price,
            quantity=data.quantity,
            date=data.date,
            fees=data.fees,
        )
        session.add(transaction)
        await session.flush()

        try:
            await self._position_service.recalculate_for_user_index(
                session, user_id, data.index_id
            )
            await session.commit()
        except InsufficientQuantityError:
            await session.rollback()
            raise
        await session.refresh(transaction)
        return TransactionRead.model_validate(transaction)

    async def update(
        self,
        session: AsyncSession,
        user_id: UUID,
        transaction_id: UUID,
        data: TransactionUpdate,
    ) -> TransactionRead:
        transaction = await self._get_user_transaction(session, user_id, transaction_id)
        old_index_id = transaction.index_id

        if data.index_id is not None:
            await self._ensure_index_exists(session, data.index_id)
            transaction.index_id = data.index_id
        if data.type is not None:
            transaction.type = data.type
        if data.price is not None:
            transaction.price = data.price
        if data.quantity is not None:
            transaction.quantity = data.quantity
        if data.date is not None:
            transaction.date = data.date
        if data.fees is not None:
            transaction.fees = data.fees

        await session.flush()

        index_ids = {old_index_id, transaction.index_id}
        try:
            for index_id in index_ids:
                await self._position_service.recalculate_for_user_index(
                    session, user_id, index_id
                )
            await session.commit()
        except InsufficientQuantityError:
            await session.rollback()
            raise
        await session.refresh(transaction)
        return TransactionRead.model_validate(transaction)

    async def delete(
        self, session: AsyncSession, user_id: UUID, transaction_id: UUID
    ) -> None:
        transaction = await self._get_user_transaction(session, user_id, transaction_id)
        index_id = transaction.index_id
        await session.delete(transaction)
        await session.flush()

        try:
            await self._position_service.recalculate_for_user_index(
                session, user_id, index_id
            )
            await session.commit()
        except InsufficientQuantityError:
            await session.rollback()
            raise

    async def _get_user_transaction(
        self, session: AsyncSession, user_id: UUID, transaction_id: UUID
    ) -> Transaction:
        transaction = await session.get(Transaction, transaction_id)
        if transaction is None or transaction.user_id != user_id:
            raise NotFoundError("Transaction not found")
        return transaction

    async def _ensure_user_exists(self, session: AsyncSession, user_id: UUID) -> None:
        user = await session.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found")

    async def _ensure_index_exists(self, session: AsyncSession, index_id: UUID) -> None:
        index = await session.get(Index, index_id)
        if index is None:
            raise NotFoundError("Index not found")
