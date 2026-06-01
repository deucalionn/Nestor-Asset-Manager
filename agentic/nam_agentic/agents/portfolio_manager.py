from langchain_core.tools import BaseTool

from nam_agentic.prompts.loader import PromptLoader
from nam_agentic.tools.registry import ToolRegistry


class PortfolioManagerAgent:
    """Configuration for the main Deep Agent (orchestrator)."""

    PROMPT_FILE = "PORTFOLIO"

    def __init__(
        self,
        tool_registry: ToolRegistry,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self._tools = tool_registry
        self._prompt_loader = prompt_loader or PromptLoader()

    def tools(self) -> list[BaseTool]:
        return []

    def system_prompt(self) -> str:
        return self._prompt_loader.load(self.PROMPT_FILE)
