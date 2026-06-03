from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IndexCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    isin: str = Field(min_length=1, max_length=12)


class IndexRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    isin: str
    created_at: datetime
