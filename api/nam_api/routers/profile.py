
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.dependencies import get_db_session, get_user_service
from nam_api.schemas.user import UserCreate, UserRead, UserUpdate
from nam_api.services.agentic_client import emit_agent_event
from nam_api.services.user_service import UserService
from nam_api.settings import settings

router = APIRouter(tags=["profile"])


@router.post("/setup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def setup_profile(
    body: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await service.setup(session, body, user_id=settings.default_user_id)
    await session.commit()
    await emit_agent_event("user.profile.created", user_id=user.id)
    return user


@router.get("/profile", response_model=UserRead)
async def get_profile(
    session: AsyncSession = Depends(get_db_session),
    service: UserService = Depends(get_user_service),
) -> UserRead:
    return await service.get_profile(session)


@router.put("/profile", response_model=UserRead)
async def update_profile(
    body: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
    service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await service.update_profile(session, body)
    await session.commit()
    await emit_agent_event("user.profile.updated", user_id=user.id)
    return user
