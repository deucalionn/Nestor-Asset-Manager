from datetime import date

from nam_db.enums import Strategy
from nam_db.models.index import Index
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


class UserFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        firstname: str = "John",
        date_of_birth: date | None = None,
        strategy: Strategy = Strategy.BALANCED,
        goals: str = "Build long-term wealth",
    ) -> User:
        user = User(
            firstname=firstname,
            date_of_birth=date_of_birth or date(1990, 1, 15),
            strategy=strategy,
            goals=goals,
        )
        session.add(user)
        await session.flush()
        return user


class IndexFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        name: str = "CAC 40",
        isin: str = "FR0003500008",
    ) -> Index:
        index = Index(name=name, isin=isin)
        session.add(index)
        await session.flush()
        return index
