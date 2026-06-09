from uuid import UUID

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.context import NamRuntimeContext
from nam_agentic.tools.market.fetch_calendar_from_bourso import FetchCalendarFromBoursoTool
from nam_agentic.tools.market.get_asset_history_from_yf import GetAssetHistoryFromYfTool
from nam_agentic.tools.market.get_asset_news_from_yf import GetAssetNewsFromYfTool
from nam_agentic.tools.market.get_asset_price_from_yf import GetAssetPriceFromYfTool
from nam_agentic.tools.market.get_company_financials_from_yf import GetCompanyFinancialsFromYfTool
from nam_agentic.tools.market.get_data_from_url import GetDataFromUrlTool
from nam_agentic.tools.market.get_etf_composition import GetEtfCompositionTool
from nam_agentic.tools.market.get_financials_news_from_bourso import GetFinancialsNewsFromBoursoTool
from nam_agentic.tools.market.search_boursorama import SearchBoursoramaTool
from nam_agentic.tools.market.search_yahoo_symbol import SearchYahooSymbolTool
from nam_agentic.tools.market.update_index_boursorama import UpdateIndexBoursoramaTool
from nam_agentic.tools.market.update_index_yahoo_symbol import UpdateIndexYahooSymbolTool
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
from nam_agentic.tools.services.market_price import MarketPriceProvider, YfinanceMarketPriceProvider
from nam_agentic.tools.services.yahoo.client import YfinanceClient


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
        yahoo_client: YfinanceClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._user_id = context.user_id
        embedding = embedding_service or OllamaEmbeddingService()
        yahoo = yahoo_client or YfinanceClient()
        prices = price_provider or YfinanceMarketPriceProvider(session_factory, client=yahoo)
        search = search_service or AnalysisSearchService()

        self.create_analysis = CreateAnalysisTool(
            session_factory, self._user_id, embedding
        ).as_tool()
        self.create_recommendation = CreateRecommendationTool(
            session_factory, self._user_id
        ).as_tool()
        self.search_past_analyses = SearchPastAnalysesTool(
            session_factory, self._user_id, embedding, search
        ).as_tool()
        self.get_user_context = GetUserContextTool(session_factory, self._user_id).as_tool()
        self.get_portfolio_positions = GetPortfolioPositionsTool(
            session_factory, self._user_id, prices
        ).as_tool()
        self.create_index = CreateIndexTool(session_factory).as_tool()
        self.get_index = GetIndexTool(session_factory).as_tool()
        self.list_indices = ListIndicesTool(session_factory).as_tool()
        self.get_financials_news_from_bourso = GetFinancialsNewsFromBoursoTool(
            session_factory, embedding
        ).as_tool()
        self.get_data_from_url = GetDataFromUrlTool(
            session_factory, embedding_service=embedding
        ).as_tool()
        self.search_boursorama = SearchBoursoramaTool(session_factory).as_tool()
        self.get_etf_composition = GetEtfCompositionTool(session_factory).as_tool()
        self.update_index_boursorama = UpdateIndexBoursoramaTool(session_factory).as_tool()
        self.get_asset_price_from_yf = GetAssetPriceFromYfTool(
            session_factory, client=yahoo
        ).as_tool()
        self.get_asset_history_from_yf = GetAssetHistoryFromYfTool(
            session_factory, client=yahoo
        ).as_tool()
        self.get_company_financials_from_yf = GetCompanyFinancialsFromYfTool(
            session_factory, client=yahoo
        ).as_tool()
        self.get_asset_news_from_yf = GetAssetNewsFromYfTool(
            session_factory, client=yahoo
        ).as_tool()
        self.search_yahoo_symbol = SearchYahooSymbolTool(
            session_factory, client=yahoo
        ).as_tool()
        self.update_index_yahoo_symbol = UpdateIndexYahooSymbolTool(session_factory).as_tool()
        self.fetch_calendar_from_bourso = FetchCalendarFromBoursoTool().as_tool()

        self._tools: list[BaseTool] = [
            self.create_analysis,
            self.create_recommendation,
            self.search_past_analyses,
            self.get_user_context,
            self.get_portfolio_positions,
            self.create_index,
            self.get_index,
            self.list_indices,
            self.get_financials_news_from_bourso,
            self.get_data_from_url,
            self.search_boursorama,
            self.get_etf_composition,
            self.update_index_boursorama,
            self.get_asset_price_from_yf,
            self.get_asset_history_from_yf,
            self.get_company_financials_from_yf,
            self.get_asset_news_from_yf,
            self.search_yahoo_symbol,
            self.update_index_yahoo_symbol,
            self.fetch_calendar_from_bourso,
        ]

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools)

    @property
    def user_id(self) -> UUID:
        return self._user_id
