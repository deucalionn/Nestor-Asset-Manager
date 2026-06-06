from datetime import datetime
from uuid import UUID

from nam_db.enums import AgentRole, AnalysisTrigger
from pydantic import BaseModel, ConfigDict


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    agent: AgentRole
    index_id: UUID | None
    title: str
    content: str
    trigger: AnalysisTrigger
    created_at: datetime


AnalysisListItem = AnalysisRead
