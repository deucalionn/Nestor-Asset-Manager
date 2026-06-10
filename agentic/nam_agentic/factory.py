from typing import Any

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    SubAgent,
    create_deep_agent,
    register_harness_profile,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from nam_agentic.agents.base import BaseSubAgent
from nam_agentic.agents.portfolio_manager import PortfolioManagerAgent
from nam_agentic.backends.shared import build_agent_backend
from nam_agentic.settings import settings

CompiledDeepAgent = CompiledStateGraph[Any, Any, Any, Any]

_harness_configured = False


def configure_nam_harness_profile() -> None:
    global _harness_configured
    if _harness_configured:
        return
    register_harness_profile(
        settings.llm_model,
        HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )
    _harness_configured = True


class DeepAgentFactory:
    """Assembles and returns the compiled NAM Deep Agent graph."""

    def __init__(
        self,
        model: str | BaseChatModel,
        portfolio_manager: PortfolioManagerAgent,
        subagents: list[BaseSubAgent],
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._model = model
        self._pm = portfolio_manager
        self._subagents = subagents
        self._checkpointer = checkpointer

    def build(self) -> CompiledDeepAgent:
        configure_nam_harness_profile()
        subagent_specs: list[SubAgent] = [agent.to_spec() for agent in self._subagents]
        return create_deep_agent(
            model=self._model,
            system_prompt=self._pm.system_prompt(),
            tools=self._pm.tools(),
            subagents=subagent_specs,
            backend=build_agent_backend(),
            checkpointer=self._checkpointer,
        )
