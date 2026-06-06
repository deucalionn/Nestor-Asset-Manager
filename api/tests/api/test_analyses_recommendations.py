import pytest
from factories import AnalysisFactory, IndexFactory, RecommendationFactory, UserFactory
from httpx import AsyncClient
from nam_db.enums import AgentRole, RecommendationStatus, RecommendationType
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def initialized_user(db_session: AsyncSession):
    user = await UserFactory.create(db_session)
    await db_session.commit()
    return user


async def test_list_analyses_empty(async_client: AsyncClient, initialized_user) -> None:
    response = await async_client.get("/analyses")

    assert response.status_code == 200
    assert response.json() == []


async def test_create_and_get_analysis(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    index = await IndexFactory.create(db_session)
    analysis = await AnalysisFactory.create(
        db_session,
        user_id=initialized_user.id,
        index_id=index.id,
        title="CAC 40 review",
    )
    await db_session.commit()

    list_response = await async_client.get("/analyses")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["title"] == "CAC 40 review"
    assert "content_embedding" not in list_response.json()[0]

    get_response = await async_client.get(f"/analyses/{analysis.id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["id"] == str(analysis.id)
    assert body["index_id"] == str(index.id)
    assert "content_embedding" not in body


async def test_filter_analyses_by_index(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    index_a = await IndexFactory.create(db_session, isin="FR0003500008")
    index_b = await IndexFactory.create(db_session, name="S&P 500", isin="US1234567890")
    await AnalysisFactory.create(
        db_session, user_id=initialized_user.id, index_id=index_a.id, title="A"
    )
    await AnalysisFactory.create(
        db_session, user_id=initialized_user.id, index_id=index_b.id, title="B"
    )
    await db_session.commit()

    response = await async_client.get(f"/analyses?index_id={index_a.id}")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "A"


async def test_get_unknown_analysis_returns_404(
    async_client: AsyncClient, initialized_user
) -> None:
    response = await async_client.get(
        "/analyses/00000000-0000-0000-0000-000000000099"
    )

    assert response.status_code == 404


async def test_list_and_get_recommendation_with_analyses(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    analysis_one = await AnalysisFactory.create(
        db_session,
        user_id=initialized_user.id,
        title="Macro view",
        agent=AgentRole.MACRO_STRATEGIST,
    )
    analysis_two = await AnalysisFactory.create(
        db_session,
        user_id=initialized_user.id,
        title="ETF view",
        agent=AgentRole.ETF_QUANT_SPECIALIST,
    )
    recommendation = await RecommendationFactory.create(
        db_session,
        user_id=initialized_user.id,
        analyses=[analysis_one, analysis_two],
        content="Combined recommendation",
        type=RecommendationType.HOLD,
    )
    await db_session.commit()

    list_response = await async_client.get("/recommendations")
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["status"] == "PENDING"
    assert len(items[0]["analyses"]) == 2

    get_response = await async_client.get(f"/recommendations/{recommendation.id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["content"] == "Combined recommendation"
    assert {item["title"] for item in body["analyses"]} == {"Macro view", "ETF view"}


async def test_filter_recommendations_by_status(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    await RecommendationFactory.create(
        db_session,
        user_id=initialized_user.id,
        status=RecommendationStatus.PENDING,
    )
    await RecommendationFactory.create(
        db_session,
        user_id=initialized_user.id,
        status=RecommendationStatus.APPLIED,
        content="Already applied",
    )
    await db_session.commit()

    response = await async_client.get("/recommendations?status=PENDING")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "PENDING"


async def test_apply_recommendation(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    recommendation = await RecommendationFactory.create(
        db_session, user_id=initialized_user.id
    )
    await db_session.commit()

    response = await async_client.patch(
        f"/recommendations/{recommendation.id}",
        json={"status": "APPLIED", "user_comment": "Executed manually"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPLIED"
    assert body["user_comment"] == "Executed manually"
    assert body["resolved_at"] is not None


async def test_reject_recommendation(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    recommendation = await RecommendationFactory.create(
        db_session, user_id=initialized_user.id
    )
    await db_session.commit()

    response = await async_client.patch(
        f"/recommendations/{recommendation.id}",
        json={"status": "REJECTED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


async def test_double_resolve_returns_409(
    async_client: AsyncClient, db_session: AsyncSession, initialized_user
) -> None:
    recommendation = await RecommendationFactory.create(
        db_session, user_id=initialized_user.id
    )
    await db_session.commit()

    first = await async_client.patch(
        f"/recommendations/{recommendation.id}",
        json={"status": "APPLIED"},
    )
    assert first.status_code == 200

    second = await async_client.patch(
        f"/recommendations/{recommendation.id}",
        json={"status": "REJECTED"},
    )
    assert second.status_code == 409
