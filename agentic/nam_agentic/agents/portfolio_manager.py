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
        """PM orchestrates only — research and financials live on subagents via task()."""
        return [
            self._tools.get_user_context,
            self._tools.get_portfolio_positions,
            self._tools.search_past_analyses,
            self._tools.list_indices,
            self._tools.get_index,
            self._tools.create_index,
            self._tools.create_recommendation,
            self._tools.fetch_calendar_from_bourso,
        ]

    def system_prompt(self) -> str:
        return self._prompt_loader.load(self.PROMPT_FILE)
