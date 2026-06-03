from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends
from nam_db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.services.user_service import UserService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


def get_user_service() -> UserService:
    return UserService()


async def get_singleton_user_id(
    session: AsyncSession = Depends(get_db_session),
    service: UserService = Depends(get_user_service),
) -> UUID:
    return await service.require_user_id(session)
