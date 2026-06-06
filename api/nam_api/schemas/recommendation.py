from datetime import datetime
from uuid import UUID

from nam_db.enums import AgentRole, RecommendationStatus, RecommendationType
from pydantic import BaseModel, ConfigDict, Field

from nam_api.schemas.analysis import AnalysisListItem


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    agent: AgentRole
    content: str
    type: RecommendationType
    status: RecommendationStatus
    user_comment: str | None
    created_at: datetime
    resolved_at: datetime | None
    analyses: list[AnalysisListItem] = Field(default_factory=list)


class RecommendationUpdate(BaseModel):
    status: RecommendationStatus
    user_comment: str | None = None
