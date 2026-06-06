from uuid import UUID

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.context import NamRuntimeContext
from nam_agentic.tools.memory.create_analysis import CreateAnalysisTool
from nam_agentic.tools.memory.create_recommendation import CreateRecommendationTool
from nam_agentic.tools.memory.search_past_analyses import SearchPastAnalysesTool
from nam_agentic.tools.portfolio.create_index import CreateIndexTool
from nam_agentic.tools.portfolio.get_index import GetIndexTool
from nam_agentic.tools.portfolio.get_positions import GetPortfolioPositionsTool
from nam_agentic.tools.portfolio.get_user_context import GetUserContextTool
from nam_agentic.tools.portfolio.list_indices import ListIndicesTool
from nam_agentic.tools.services.analysis_search import AnalysisSearchService
from nam_agentic.tools.services.embedding import EmbeddingService, OllamaEmbeddingService
from nam_agentic.tools.services.market_price import MarketPriceProvider, StubMarketPriceProvider


class ToolRegistry:
    """Instantiates basics-tools bound to runtime context."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        context: NamRuntimeContext,
        *,
        embedding_service: EmbeddingService | None = None,
        price_provider: MarketPriceProvider | None = None,
        search_service: AnalysisSearchService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._user_id = context.user_id
        embedding = embedding_service or OllamaEmbeddingService()
        prices = price_provider or StubMarketPriceProvider()
        search = search_service or AnalysisSearchService()

        self._tools: list[BaseTool] = [
            CreateAnalysisTool(session_factory, self._user_id, embedding).as_tool(),
            CreateRecommendationTool(session_factory, self._user_id).as_tool(),
            SearchPastAnalysesTool(
                session_factory, self._user_id, embedding, search
            ).as_tool(),
            GetUserContextTool(session_factory, self._user_id).as_tool(),
            GetPortfolioPositionsTool(session_factory, self._user_id, prices).as_tool(),
            CreateIndexTool(session_factory).as_tool(),
            GetIndexTool(session_factory).as_tool(),
            ListIndicesTool(session_factory).as_tool(),
        ]

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools)

    @property
    def user_id(self) -> UUID:
        return self._user_id
