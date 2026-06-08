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
        return "Analyzes macroeconomic trends, rates, and geopolitical risk."

    @property
    def prompt_file(self) -> str:
        return "MACRO_STRATEGIST"

    def tools(self) -> list[BaseTool]:
        return [
            self._tools.create_analysis,
            self._tools.search_past_analyses,
        ]
