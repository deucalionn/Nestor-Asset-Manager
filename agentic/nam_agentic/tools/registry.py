from sqlalchemy.ext.asyncio import async_sessionmaker


class ToolRegistry:
    """Central registry — injects DB session into tool classes (stub)."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory
