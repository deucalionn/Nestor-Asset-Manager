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
        return []
