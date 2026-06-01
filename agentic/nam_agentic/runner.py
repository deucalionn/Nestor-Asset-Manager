from collections.abc import AsyncIterator

from nam_agentic.context import NamRuntimeContext
from nam_agentic.factory import DeepAgentFactory


class AgentRunner:
    """Thin wrapper around the compiled Deep Agent graph."""

    def __init__(self, factory: DeepAgentFactory) -> None:
        self._agent = factory.build()

    async def invoke(self, message: str, context: NamRuntimeContext) -> dict:
        return await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            context=context,
        )

    async def stream(self, message: str, context: NamRuntimeContext) -> AsyncIterator:
        async for chunk in self._agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            context=context,
        ):
            yield chunk
