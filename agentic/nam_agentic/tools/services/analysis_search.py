from uuid import UUID

from nam_db.enums import AgentRole
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from nam_agentic.tools.schemas.memory import AnalysisSearchResult


class AnalysisSearchService:
    async def search(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        query_vector: list[float],
        top_k: int,
        agent_filter: AgentRole | None,
        min_similarity: float,
    ) -> list[AnalysisSearchResult]:
        vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"
        params: dict = {
            "query_vec": vector_literal,
            "user_id": user_id,
            "min_similarity": min_similarity,
            "top_k": top_k,
        }
        agent_clause = ""
        if agent_filter is not None:
            agent_clause = "AND agent = :agent_filter"
            params["agent_filter"] = agent_filter.value

        stmt = text(
            f"""
            SELECT id, agent, title, content, created_at,
                   1 - (content_embedding <=> CAST(:query_vec AS vector)) AS similarity
            FROM analyses
            WHERE user_id = :user_id
              {agent_clause}
              AND 1 - (content_embedding <=> CAST(:query_vec AS vector)) >= :min_similarity
            ORDER BY content_embedding <=> CAST(:query_vec AS vector)
            LIMIT :top_k
            """
        )
        result = await session.execute(stmt, params)
        rows = result.mappings().all()
        return [
            AnalysisSearchResult(
                analysis_id=row["id"],
                agent=AgentRole(row["agent"]),
                title=row["title"],
                content_snippet=_snippet(row["content"]),
                similarity_score=float(row["similarity"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]


def _snippet(content: str, max_len: int = 200) -> str:
    text_content = content.strip()
    if len(text_content) <= max_len:
        return text_content
    return text_content[: max_len - 3].rstrip() + "..."
