from uuid import uuid4

import pytest
from factories import UserFactory
from httpx import AsyncClient
from nam_api.main import app
from nam_db.models.chat_thread import ChatThread
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def initialized_user(db_session: AsyncSession):
    user = await UserFactory.create(db_session)
    await db_session.commit()
    return user


@pytest.fixture
async def chat_thread(db_session: AsyncSession, initialized_user) -> ChatThread:
    thread = ChatThread(
        id=uuid4(),
        user_id=initialized_user.id,
        title="US market news",
    )
    db_session.add(thread)
    await db_session.commit()
    return thread


async def test_list_chat_threads_empty(async_client: AsyncClient, initialized_user) -> None:
    response = await async_client.get("/chat/threads")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_and_list_chat_thread(async_client: AsyncClient, initialized_user) -> None:
    create = await async_client.post("/chat/threads", json={})
    assert create.status_code == 201
    body = create.json()
    assert body["title"] == "New conversation"

    listing = await async_client.get("/chat/threads")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_delete_chat_thread(
    async_client: AsyncClient,
    initialized_user,
    chat_thread: ChatThread,
) -> None:
    response = await async_client.delete(f"/chat/threads/{chat_thread.id}")
    assert response.status_code == 204

    listing = await async_client.get("/chat/threads")
    assert listing.json() == []
