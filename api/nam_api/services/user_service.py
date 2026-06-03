from uuid import UUID

from nam_db.models.user import User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.exceptions import AlreadyInitializedError, SetupRequiredError
from nam_api.schemas.user import UserCreate, UserRead, UserUpdate


class UserService:
    async def setup(
        self, session: AsyncSession, data: UserCreate, *, user_id: UUID | None = None
    ) -> UserRead:
        count = await session.scalar(select(func.count()).select_from(User))
        if count and count > 0:
            raise AlreadyInitializedError()

        user = User(
            firstname=data.firstname,
            date_of_birth=data.date_of_birth,
            strategy=data.strategy,
            goals=data.goals,
        )
        if user_id is not None:
            user.id = user_id
        session.add(user)
        await session.flush()
        return UserRead.model_validate(user)

    async def get_profile(self, session: AsyncSession) -> UserRead:
        user = await self._get_singleton(session)
        return UserRead.model_validate(user)

    async def update_profile(self, session: AsyncSession, data: UserUpdate) -> UserRead:
        user = await self._get_singleton(session)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await session.flush()
        await session.refresh(user)
        return UserRead.model_validate(user)

    async def require_user_id(self, session: AsyncSession) -> UUID:
        user = await self._get_singleton(session)
        return user.id

    async def _get_singleton(self, session: AsyncSession) -> User:
        result = await session.execute(select(User).limit(2))
        users = list(result.scalars().all())
        if not users:
            raise SetupRequiredError()
        if len(users) > 1:
            msg = "Multiple users found — single-user deployment supports one profile only"
            raise SetupRequiredError(msg)
        return users[0]
