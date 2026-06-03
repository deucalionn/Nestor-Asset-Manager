import pytest
from factories import UserFactory
from nam_api.exceptions import AlreadyInitializedError, SetupRequiredError
from nam_api.schemas.user import UserCreate, UserUpdate
from nam_api.services.user_service import UserService
from nam_db.enums import Strategy
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def service() -> UserService:
    return UserService()


SETUP_PAYLOAD = {
    "firstname": "Lucas",
    "date_of_birth": "1990-01-15",
    "strategy": "BALANCED",
    "goals": "Retire early",
}


async def test_setup_creates_singleton_user(
    db_session: AsyncSession, service: UserService
) -> None:
    user = await service.setup(db_session, UserCreate.model_validate(SETUP_PAYLOAD))
    await db_session.commit()

    assert user.firstname == "Lucas"
    assert user.strategy == Strategy.BALANCED


async def test_setup_rejects_second_user(
    db_session: AsyncSession, service: UserService
) -> None:
    await service.setup(db_session, UserCreate.model_validate(SETUP_PAYLOAD))
    await db_session.commit()

    with pytest.raises(AlreadyInitializedError):
        await service.setup(db_session, UserCreate.model_validate(SETUP_PAYLOAD))


async def test_require_user_id_without_setup(
    db_session: AsyncSession, service: UserService
) -> None:
    with pytest.raises(SetupRequiredError):
        await service.require_user_id(db_session)


async def test_update_profile(db_session: AsyncSession, service: UserService) -> None:
    await UserFactory.create(db_session, firstname="Before")
    await db_session.commit()

    updated = await service.update_profile(
        db_session, UserUpdate(goals="New goals")
    )
    await db_session.commit()

    assert updated.firstname == "Before"
    assert updated.goals == "New goals"
