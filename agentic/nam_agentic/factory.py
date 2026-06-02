from typing import Any

from deepagents import SubAgent, create_deep_agent
from langgraph.graph.state import CompiledStateGraph

from nam_agentic.agents.base import BaseSubAgent
from nam_agentic.agents.portfolio_manager import PortfolioManagerAgent

CompiledDeepAgent = CompiledStateGraph[Any, Any, Any, Any]


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

    def build(self) -> CompiledDeepAgent:
        subagent_specs: list[SubAgent] = [agent.to_spec() for agent in self._subagents]
        return create_deep_agent(
            model=self._model,
            system_prompt=self._pm.system_prompt(),
            tools=self._pm.tools(),
            subagents=subagent_specs,
        )
