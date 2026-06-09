from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.enums import AgentRole
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.memory import SearchPastAnalysesInput, SearchPastAnalysesOutput
from nam_agentic.tools.services.analysis_search import AnalysisSearchService
from nam_agentic.tools.services.embedding import EmbeddingService


class SearchPastAnalysesTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        user_id: UUID,
        embedding_service: EmbeddingService,
        search_service: AnalysisSearchService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._user_id = user_id
        self._embedding_service = embedding_service
        self._search_service = search_service or AnalysisSearchService()

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        user_id = self._user_id
        embedding_service = self._embedding_service
        search_service = self._search_service

        @tool(args_schema=SearchPastAnalysesInput)
        async def search_past_analyses(
            query: str,
            top_k: int = 5,
            agent_filter: AgentRole | None = None,
            min_similarity: float = 0.7,
        ) -> SearchPastAnalysesOutput:
            """Search past analyses by semantic similarity (RAG).

            Use when: grounding a new memo in your prior regime or stock theses.
            Do not use when: you need live market news — use get_financials_news_from_bourso
            or get_asset_news_from_yf instead.
            Returns: ranked analyses with title, agent, content excerpt, and dates.
            """
            query_vector = await embedding_service.embed(query)
            async with session_factory() as session:
                results = await search_service.search(
                    session,
                    user_id=user_id,
                    query_vector=query_vector,
                    top_k=top_k,
                    agent_filter=agent_filter,
                    min_similarity=min_similarity,
                )
            return SearchPastAnalysesOutput(results=results)

        return search_past_analyses
