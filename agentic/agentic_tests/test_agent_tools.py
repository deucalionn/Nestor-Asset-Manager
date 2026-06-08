import pytest
from nam_agentic.agents.etf_quant import EtfQuantSpecialistAgent
from nam_agentic.agents.macro_strategist import MacroStrategistAgent
from nam_agentic.agents.portfolio_manager import PortfolioManagerAgent
from nam_agentic.agents.sector_analyst import SectorAnalystAgent
from nam_agentic.context import NamRuntimeContext
from nam_agentic.tools.registry import ToolRegistry
from nam_db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


def _tool_names(tools) -> set[str]:
    return {tool.name for tool in tools}


async def test_portfolio_manager_tools(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    registry = ToolRegistry(session_factory, NamRuntimeContext(user_id=test_user.id))
    pm = PortfolioManagerAgent(registry)

    assert _tool_names(pm.tools()) == {
        "get_user_context",
        "get_portfolio_positions",
        "create_recommendation",
        "create_index",
    }


async def test_subagent_tools(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    registry = ToolRegistry(session_factory, NamRuntimeContext(user_id=test_user.id))
    expected = {"create_analysis", "search_past_analyses"}

    for agent_cls in (SectorAnalystAgent, MacroStrategistAgent, EtfQuantSpecialistAgent):
        agent = agent_cls(registry)
        assert _tool_names(agent.tools()) == expected
