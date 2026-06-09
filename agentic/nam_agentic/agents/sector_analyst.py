from langchain_core.tools import BaseTool

from nam_agentic.agents.base import BaseSubAgent
from nam_agentic.tools.registry import ToolRegistry


class SectorAnalystAgent(BaseSubAgent):
    def __init__(self, tool_registry: ToolRegistry, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tools = tool_registry

    @property
    def name(self) -> str:
        return "sector-analyst"

    @property
    def description(self) -> str:
        return "Analyzes individual equities, sectors, and company fundamentals."

    @property
    def prompt_file(self) -> str:
        return "SECTOR_ANALYST"

    def tools(self) -> list[BaseTool]:
        return [
            self._tools.create_analysis,
            self._tools.search_past_analyses,
            self._tools.get_financials_news_from_bourso,
            self._tools.get_data_from_url,
            self._tools.search_boursorama,
            self._tools.update_index_boursorama,
            self._tools.get_index,
            self._tools.get_portfolio_positions,
            self._tools.get_asset_price_from_yf,
            self._tools.get_asset_history_from_yf,
            self._tools.get_asset_news_from_yf,
            self._tools.get_company_financials_from_yf,
            self._tools.search_yahoo_symbol,
            self._tools.update_index_yahoo_symbol,
        ]
