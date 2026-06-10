from uuid import UUID, uuid4

from nam_db.models.chat_thread import ChatThread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_THREAD_TITLE = "New conversation"


def truncate_title(content: str, *, max_len: int = 60) -> str:
    text = " ".join(content.strip().split())
    if not text:
        return DEFAULT_THREAD_TITLE
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


class ChatThreadService:
    async def list_for_user(self, session: AsyncSession, user_id: UUID) -> list[ChatThread]:
        stmt = (
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(ChatThread.updated_at.desc())
        )
        return list(await session.scalars(stmt))

    async def create(
        self,
        session: AsyncSession,
        user_id: UUID,
        *,
        title: str | None = None,
        thread_id: UUID | None = None,
    ) -> ChatThread:
        thread = ChatThread(
            id=thread_id or uuid4(),
            user_id=user_id,
            title=title or DEFAULT_THREAD_TITLE,
        )
        session.add(thread)
        await session.flush()
        return thread

    async def get(
        self, session: AsyncSession, user_id: UUID, thread_id: UUID
    ) -> ChatThread | None:
        return await session.get(ChatThread, thread_id)

    async def require(
        self, session: AsyncSession, user_id: UUID, thread_id: UUID
    ) -> ChatThread:
        thread = await self.get(session, user_id, thread_id)
        if thread is None or thread.user_id != user_id:
            from nam_api.exceptions import NotFoundError

            raise NotFoundError("Conversation not found")
        return thread

    async def update_title(
        self,
        session: AsyncSession,
        user_id: UUID,
        thread_id: UUID,
        title: str,
    ) -> ChatThread:
        thread = await self.require(session, user_id, thread_id)
        thread.title = title
        await session.flush()
        return thread

    async def delete(self, session: AsyncSession, user_id: UUID, thread_id: UUID) -> None:
        thread = await self.require(session, user_id, thread_id)
        await session.delete(thread)

    async def touch_after_message(
        self,
        session: AsyncSession,
        user_id: UUID,
        thread_id: UUID,
        user_message: str,
    ) -> ChatThread:
        thread = await self.get(session, user_id, thread_id)
        if thread is None:
            thread = await self.create(
                session,
                user_id,
                thread_id=thread_id,
                title=truncate_title(user_message),
            )
            return thread
        if thread.title == DEFAULT_THREAD_TITLE:
            thread.title = truncate_title(user_message)
        await session.flush()
        return thread
