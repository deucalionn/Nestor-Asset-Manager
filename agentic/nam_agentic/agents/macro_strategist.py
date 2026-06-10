from langchain_core.tools import BaseTool

from nam_agentic.agents.base import BaseSubAgent
from nam_agentic.tools.registry import ToolRegistry


class MacroStrategistAgent(BaseSubAgent):
    def __init__(self, tool_registry: ToolRegistry, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tools = tool_registry

    @property
    def name(self) -> str:
        return "macro-strategist"

    @property
    def description(self) -> str:
        return (
            "Macro and market headlines: rates, geopolitics, broad indices, session recap. "
            "Uses get_financials_news_from_bourso, Yahoo news/prices. "
            "Use for 'what's new on markets' — not single-stock fundamentals."
        )

    @property
    def prompt_file(self) -> str:
        return "MACRO_STRATEGIST"

    def tools(self) -> list[BaseTool]:
        return [
            self._tools.create_analysis,
            self._tools.search_past_analyses,
            self._tools.get_financials_news_from_bourso,
            self._tools.get_data_from_url,
            self._tools.get_asset_price_from_yf,
            self._tools.get_asset_history_from_yf,
            self._tools.get_asset_news_from_yf,
        ]
