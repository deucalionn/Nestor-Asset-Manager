from datetime import date
from uuid import UUID

from nam_db.enums import (
    AgentRole,
    AnalysisTrigger,
    RecommendationStatus,
    RecommendationType,
    Strategy,
)
from nam_db.models.analysis import Analysis
from nam_db.models.index import Index
from nam_db.models.recommendation import Recommendation
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

EMBEDDING_DIM = 384


def zero_embedding() -> list[float]:
    return [0.0] * EMBEDDING_DIM


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
        yahoo_symbol: str | None = None,
    ) -> Index:
        index = Index(name=name, isin=isin, yahoo_symbol=yahoo_symbol)
        session.add(index)
        await session.flush()
        return index


class AnalysisFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        user_id: UUID,
        agent: AgentRole = AgentRole.SECTOR_ANALYST,
        index_id: UUID | None = None,
        title: str = "Sector outlook",
        content: str = "Detailed sector analysis report.",
        trigger: AnalysisTrigger = AnalysisTrigger.MARKET_SESSION,
    ) -> Analysis:
        analysis = Analysis(
            user_id=user_id,
            agent=agent,
            index_id=index_id,
            title=title,
            content=content,
            content_embedding=zero_embedding(),
            trigger=trigger,
        )
        session.add(analysis)
        await session.flush()
        return analysis


class RecommendationFactory:
    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        user_id: UUID,
        analyses: list[Analysis] | None = None,
        agent: AgentRole = AgentRole.PORTFOLIO_MANAGER,
        content: str = "Increase exposure based on sub-agent reports.",
        type: RecommendationType = RecommendationType.BUY,
        status: RecommendationStatus = RecommendationStatus.PENDING,
    ) -> Recommendation:
        recommendation = Recommendation(
            user_id=user_id,
            agent=agent,
            content=content,
            type=type,
            status=status,
        )
        if analyses:
            recommendation.analyses = analyses
        session.add(recommendation)
        await session.flush()
        return recommendation
