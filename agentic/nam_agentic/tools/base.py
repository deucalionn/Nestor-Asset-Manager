from abc import ABC, abstractmethod

from langchain_core.tools import BaseTool


class BaseNamTool(ABC):
    """Base class for NAM custom tools."""

    @abstractmethod
    def as_tool(self) -> BaseTool:
        """Return the LangChain tool callable bound to this instance."""
