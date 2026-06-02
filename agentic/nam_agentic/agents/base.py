from abc import ABC, abstractmethod

from deepagents import SubAgent
from langchain_core.tools import BaseTool

from nam_agentic.prompts.loader import PromptLoader


class BaseSubAgent(ABC):
    """Base class for all NAM subagents."""

    def __init__(self, prompt_loader: PromptLoader | None = None) -> None:
        self._prompt_loader = prompt_loader or PromptLoader()

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier used by the PM's task() tool."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Action-oriented description — PM uses this to decide delegation."""

    @property
    @abstractmethod
    def prompt_file(self) -> str:
        """Markdown prompt filename without extension (e.g. SECTOR_ANALYST)."""

    @abstractmethod
    def tools(self) -> list[BaseTool]:
        """Return LangChain tools available to this subagent."""

    def system_prompt(self) -> str:
        return self._prompt_loader.load(self.prompt_file)

    def to_spec(self) -> SubAgent:
        """Convert to Deep Agents declarative subagent spec."""
        return SubAgent(
            name=self.name,
            description=self.description,
            system_prompt=self.system_prompt(),
            tools=self.tools(),
        )
