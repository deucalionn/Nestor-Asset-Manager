from nam_db.enums import NewsCategory, NewsSource
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from nam_agentic.tools.schemas.market import NewsItemOutput


class NewsSearchService:
    async def search(
        self,
        session: AsyncSession,
        *,
        query_vector: list[float],
        since_hours: int,
        top_k: int,
        min_similarity: float,
        category: NewsCategory | None,
        boursorama_ticker: str | None,
        keyword: str | None,
    ) -> list[NewsItemOutput]:
        vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"
        params: dict = {
            "query_vec": vector_literal,
            "since_hours": since_hours,
            "min_similarity": min_similarity,
            "top_k": top_k,
        }
        filters = [
            "content_embedding IS NOT NULL",
            "fetched_at >= NOW() - make_interval(hours => :since_hours)",
            "1 - (content_embedding <=> CAST(:query_vec AS vector)) >= :min_similarity",
        ]
        if category is not None:
            filters.append("category = :category")
            params["category"] = category.value
        if boursorama_ticker:
            filters.append("boursorama_ticker = :boursorama_ticker")
            params["boursorama_ticker"] = boursorama_ticker
        if keyword:
            pattern = f"%{keyword}%"
            filters.append("(title ILIKE :keyword OR summary ILIKE :keyword)")
            params["keyword"] = pattern

        where_clause = " AND ".join(filters)
        stmt = text(
            f"""
            SELECT id, source, category, title, source_url, summary, boursorama_ticker,
                   published_at, fetched_at,
                   1 - (content_embedding <=> CAST(:query_vec AS vector)) AS similarity
            FROM news_items
            WHERE {where_clause}
            ORDER BY content_embedding <=> CAST(:query_vec AS vector)
            LIMIT :top_k
            """
        )
        result = await session.execute(stmt, params)
        rows = result.mappings().all()
        return [
            NewsItemOutput(
                id=row["id"],
                source=NewsSource(row["source"]),
                category=NewsCategory(row["category"]),
                title=row["title"],
                source_url=row["source_url"],
                summary=row["summary"],
                boursorama_ticker=row["boursorama_ticker"],
                published_at=row["published_at"],
                fetched_at=row["fetched_at"],
                similarity_score=float(row["similarity"]),
            )
            for row in rows
        ]
