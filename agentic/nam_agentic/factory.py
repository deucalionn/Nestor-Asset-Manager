from deepagents import create_deep_agent

from nam_agentic.agents.base import BaseSubAgent
from nam_agentic.agents.portfolio_manager import PortfolioManagerAgent


class DeepAgentFactory:
    """Assembles and returns the compiled NAM Deep Agent graph."""

    def __init__(
        self,
        model: str,
        portfolio_manager: PortfolioManagerAgent,
        subagents: list[BaseSubAgent],
    ) -> None:
        self._model = model
        self._pm = portfolio_manager
        self._subagents = subagents

    def build(self):
        return create_deep_agent(
            model=self._model,
            system_prompt=self._pm.system_prompt(),
            tools=self._pm.tools(),
            subagents=[agent.to_spec() for agent in self._subagents],
        )
