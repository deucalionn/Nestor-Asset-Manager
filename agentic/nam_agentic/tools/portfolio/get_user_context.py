from datetime import date
from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.errors import ToolError
from nam_agentic.tools.schemas.portfolio import EmptyToolInput, UserContextOutput


def _compute_age(date_of_birth: date) -> int:
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


class GetUserContextTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        user_id: UUID,
    ) -> None:
        self._session_factory = session_factory
        self._user_id = user_id

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        user_id = self._user_id

        @tool(args_schema=EmptyToolInput)
        async def get_user_context() -> UserContextOutput:
            """Return the configured user profile (strategy, goals, age)."""
            async with session_factory() as session:
                user = await session.get(User, user_id)
                if user is None:
                    raise ToolError("User not found")

            return UserContextOutput(
                user_id=user.id,
                firstname=user.firstname,
                date_of_birth=user.date_of_birth,
                age=_compute_age(user.date_of_birth),
                strategy=user.strategy,
                goals=user.goals,
            )

        return get_user_context
