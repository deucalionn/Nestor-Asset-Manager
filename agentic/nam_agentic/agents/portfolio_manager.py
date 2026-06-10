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
        return [
            self._tools.get_user_context,
            self._tools.get_portfolio_positions,
            self._tools.search_past_analyses,
            self._tools.list_indices,
            self._tools.get_index,
            self._tools.create_index,
            self._tools.create_recommendation,
            self._tools.fetch_calendar_from_bourso,
            self._tools.get_financials_news_from_bourso,
            self._tools.get_asset_news_from_yf,
            self._tools.search_boursorama,
            self._tools.get_data_from_url,
        ]

    def system_prompt(self) -> str:
        base = self._prompt_loader.load(self.PROMPT_FILE)
        chat = self._prompt_loader.load("CHAT")
        return f"{base}\n\n---\n\n{chat}"
