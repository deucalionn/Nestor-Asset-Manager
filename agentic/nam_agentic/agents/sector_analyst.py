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
        return []
