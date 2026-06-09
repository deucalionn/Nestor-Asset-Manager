from datetime import datetime
from uuid import UUID

from nam_db.enums import IndexType
from pydantic import BaseModel, ConfigDict, Field


class IndexCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    isin: str = Field(min_length=1, max_length=12)
    index_type: IndexType
    boursorama_ticker: str | None = Field(default=None, max_length=32)
    yahoo_symbol: str | None = Field(default=None, max_length=32)


class IndexRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    isin: str
    index_type: IndexType
    boursorama_ticker: str | None
    yahoo_symbol: str | None
    created_at: datetime
