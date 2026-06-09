import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

DEFAULT_TEST_DATABASE_URL = "postgresql+asyncpg://nam:nam@localhost:5432/nam_test"

TRUNCATE_TABLES = (
    "recommendation_analyses",
    "recommendations",
    "analyses",
    "news_items",
    "positions",
    "transactions",
    "indices",
    "users",
)


def get_test_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


async def truncate_test_tables(engine: AsyncEngine) -> None:
    table_list = ", ".join(TRUNCATE_TABLES)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))
