from datetime import date
from uuid import uuid4

import pytest
from nam_agentic.tools.memory.create_analysis import CreateAnalysisTool
from nam_agentic.tools.memory.create_recommendation import CreateRecommendationTool
from nam_agentic.tools.memory.search_past_analyses import SearchPastAnalysesTool
from nam_db.enums import (
    AgentRole,
    AnalysisTrigger,
    RecommendationStatus,
    RecommendationType,
    SubAgentRole,
)
from nam_db.models.analysis import Analysis
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from support.helpers import EMBEDDING_DIM, MockEmbeddingService, as_dict

pytestmark = pytest.mark.asyncio


async def test_create_analysis_persists_row(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    mock_embedding: MockEmbeddingService,
) -> None:
    tool = CreateAnalysisTool(session_factory, test_user.id, mock_embedding).as_tool()
    result = as_dict(
        await tool.ainvoke(
            {
                "agent": SubAgentRole.SECTOR_ANALYST.value,
                "title": "Tech sector",
                "content": "C" * 100,
                "trigger": AnalysisTrigger.MARKET_SESSION.value,
            }
        )
    )

    assert result["embedding_dimensions"] == EMBEDDING_DIM
    assert result["agent"] == AgentRole.SECTOR_ANALYST.value


async def test_create_recommendation_links_analyses(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    test_analysis: Analysis,
) -> None:
    tool = CreateRecommendationTool(session_factory, test_user.id).as_tool()
    result = as_dict(
        await tool.ainvoke(
            {
                "analysis_ids": [str(test_analysis.id)],
                "content": "R" * 50,
                "type": RecommendationType.BUY.value,
            }
        )
    )

    assert result["status"] == RecommendationStatus.PENDING.value


async def test_create_recommendation_rejects_foreign_analysis(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    tool = CreateRecommendationTool(session_factory, test_user.id).as_tool()
    with pytest.raises(Exception):
        await tool.ainvoke(
            {
                "analysis_ids": [str(uuid4())],
                "content": "R" * 50,
                "type": RecommendationType.BUY.value,
            }
        )


async def test_search_past_analyses_user_isolation(
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
    test_user: User,
    test_analysis: Analysis,
) -> None:
    other = User(
        firstname="Other",
        date_of_birth=date(1985, 1, 1),
        strategy=test_user.strategy,
        goals="Other goals",
    )
    db_session.add(other)
    await db_session.commit()

    similar = Analysis(
        user_id=other.id,
        agent=AgentRole.MACRO_STRATEGIST,
        title="Other macro",
        content="B" * 100,
        content_embedding=[1.0] + [0.0] * (EMBEDDING_DIM - 1),
        trigger=AnalysisTrigger.MANUAL,
    )
    db_session.add(similar)
    await db_session.commit()

    tool = SearchPastAnalysesTool(
        session_factory, test_user.id, MockEmbeddingService()
    ).as_tool()
    result = as_dict(
        await tool.ainvoke(
            {
                "query": "macro economic outlook",
                "top_k": 5,
                "min_similarity": 0.0,
            }
        )
    )

    ids = {row["analysis_id"] for row in result["results"]}
    assert str(test_analysis.id) in ids
    assert str(similar.id) not in ids


async def test_langchain_schemas_exclude_user_id(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    mock_embedding: MockEmbeddingService,
) -> None:
    tools = [
        CreateAnalysisTool(session_factory, test_user.id, mock_embedding).as_tool(),
        CreateRecommendationTool(session_factory, test_user.id).as_tool(),
        SearchPastAnalysesTool(session_factory, test_user.id, mock_embedding).as_tool(),
    ]
    for langchain_tool in tools:
        assert langchain_tool.args_schema is not None
        assert "user_id" not in langchain_tool.args_schema.model_fields
