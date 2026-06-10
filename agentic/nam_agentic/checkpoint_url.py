def to_psycopg_conn_string(database_url: str) -> str:
    """Convert SQLAlchemy async URL to a psycopg-compatible DSN."""
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return database_url
