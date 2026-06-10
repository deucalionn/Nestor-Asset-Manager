from langgraph.checkpoint.base import BaseCheckpointSaver

from nam_agentic.agents.etf_quant import EtfQuantSpecialistAgent
from nam_agentic.agents.macro_strategist import MacroStrategistAgent
from nam_agentic.agents.portfolio_manager import PortfolioManagerAgent
from nam_agentic.agents.sector_analyst import SectorAnalystAgent
from nam_agentic.factory import DeepAgentFactory
from nam_agentic.llm import build_chat_model
from nam_agentic.tools.registry import ToolRegistry


def build_deep_agent_factory(
    registry: ToolRegistry,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
) -> DeepAgentFactory:
    portfolio_manager = PortfolioManagerAgent(registry)
    subagents = [
        SectorAnalystAgent(registry),
        MacroStrategistAgent(registry),
        EtfQuantSpecialistAgent(registry),
    ]
    return DeepAgentFactory(
        model=build_chat_model(),
        portfolio_manager=portfolio_manager,
        subagents=subagents,
        checkpointer=checkpointer,
    )
