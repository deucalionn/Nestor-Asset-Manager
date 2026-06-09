from langchain_core.tools import BaseTool

from nam_agentic.agents.base import BaseSubAgent
from nam_agentic.tools.registry import ToolRegistry


class EtfQuantSpecialistAgent(BaseSubAgent):
    def __init__(self, tool_registry: ToolRegistry, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tools = tool_registry

    @property
    def name(self) -> str:
        return "etf-quant"

    @property
    def description(self) -> str:
        return "Evaluates ETF exposure, factor tilts, and quantitative signals."

    @property
    def prompt_file(self) -> str:
        return "ETF_QUANT"

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
            self._tools.get_etf_composition,
            self._tools.get_asset_price_from_yf,
            self._tools.get_asset_history_from_yf,
            self._tools.get_asset_news_from_yf,
        ]
