from abc import ABC, abstractmethod

from langchain_core.tools import BaseTool


class BaseNamTool(ABC):
    """Base class for NAM custom tools.

    Tool docstrings are LLM-facing descriptions. Use this template:

        \"\"\"<One-line imperative summary>.

        Use when: <concrete trigger situations>.
        Do not use when: <anti-patterns or superseding tools>.
        Returns: <output shape in plain language>.
        \"\"\"
    """

    @abstractmethod
    def as_tool(self) -> BaseTool:
        """Return the LangChain tool callable bound to this instance."""
