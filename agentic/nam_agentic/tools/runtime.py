from dataclasses import dataclass
from uuid import UUID

from nam_agentic.context import NamRuntimeContext


@dataclass(frozen=True)
class ToolRuntime:
    user_id: UUID

    @classmethod
    def from_context(cls, context: NamRuntimeContext) -> "ToolRuntime":
        return cls(user_id=context.user_id)
