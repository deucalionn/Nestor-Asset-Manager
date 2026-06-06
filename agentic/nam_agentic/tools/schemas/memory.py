from datetime import datetime
from uuid import UUID

from nam_db.enums import (
    AgentRole,
    AnalysisTrigger,
    RecommendationStatus,
    RecommendationType,
    SubAgentRole,
)
from pydantic import BaseModel, Field


class CreateAnalysisInput(BaseModel):
    agent: SubAgentRole
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=100)
    trigger: AnalysisTrigger
    index_id: UUID | None = None


class CreateAnalysisOutput(BaseModel):
    analysis_id: UUID
    agent: AgentRole
    embedding_dimensions: int
    created_at: datetime


class CreateRecommendationInput(BaseModel):
    analysis_ids: list[UUID] = Field(min_length=1)
    content: str = Field(min_length=50)
    type: RecommendationType


class CreateRecommendationOutput(BaseModel):
    recommendation_id: UUID
    status: RecommendationStatus
    created_at: datetime


class SearchPastAnalysesInput(BaseModel):
    query: str = Field(min_length=10)
    top_k: int = Field(default=5, ge=1, le=20)
    agent_filter: AgentRole | None = None
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)


class AnalysisSearchResult(BaseModel):
    analysis_id: UUID
    agent: AgentRole
    title: str
    content_snippet: str
    similarity_score: float
    created_at: datetime


class SearchPastAnalysesOutput(BaseModel):
    results: list[AnalysisSearchResult]
