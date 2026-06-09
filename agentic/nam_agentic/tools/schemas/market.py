from datetime import datetime
from decimal import Decimal
from uuid import UUID

from nam_db.enums import IndexType, NewsCategory, NewsSource
from pydantic import BaseModel, ConfigDict, Field, model_validator


class GetFinancialsNewsInput(BaseModel):
    category: NewsCategory | None = None
    keyword: str | None = None
    semantic_query: str | None = Field(
        default=None,
        description="Natural-language query for pgvector similarity search.",
    )
    since_hours: int = Field(default=48, ge=1, le=168)
    boursorama_ticker: str | None = None
    limit: int = Field(default=20, ge=1, le=50)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)


class NewsItemOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: NewsSource
    category: NewsCategory
    title: str
    source_url: str
    summary: str | None
    boursorama_ticker: str | None
    published_at: datetime | None
    fetched_at: datetime
    similarity_score: float | None = None


class GetFinancialsNewsOutput(BaseModel):
    items: list[NewsItemOutput]
    count: int


class GetDataFromUrlInput(BaseModel):
    url: str = Field(max_length=2048)
    persist: bool = Field(
        default=True,
        description="When true, upsert article deep-reads into news_items with embedding.",
    )


class CompanyNewsHeadlineOutput(BaseModel):
    title: str
    summary: str
    article_url: str
    published_at: datetime | None
    attribution: str | None


class GetDataFromUrlOutput(BaseModel):
    url: str
    title: str
    content_type: str
    headlines: list[CompanyNewsHeadlineOutput] | None = None
    markdown: str | None = None
    fetched_at: datetime
    persisted: bool = False
    news_item_id: UUID | None = None


class SearchBoursoramaInput(BaseModel):
    query: str | None = None
    isin: str | None = None
    index_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one_key(self) -> "SearchBoursoramaInput":
        keys = [self.query is not None, self.isin is not None, self.index_id is not None]
        if sum(keys) != 1:
            msg = "Exactly one of query, isin, or index_id must be provided"
            raise ValueError(msg)
        return self


class SearchBoursoramaOutput(BaseModel):
    boursorama_ticker: str
    name: str
    isin: str | None
    index_id: UUID | None
    index_type: IndexType
    quote_url: str
    news_url: str | None
    key_figures_url: str | None
    composition_url: str | None
    resolved_from_db: bool


class GetEtfCompositionInput(BaseModel):
    index_id: UUID | None = None
    boursorama_ticker: str | None = None

    @model_validator(mode="after")
    def exactly_one_key(self) -> "GetEtfCompositionInput":
        keys = [self.index_id is not None, self.boursorama_ticker is not None]
        if sum(keys) != 1:
            msg = "Exactly one of index_id or boursorama_ticker must be provided"
            raise ValueError(msg)
        return self


class EtfHoldingItem(BaseModel):
    name: str
    weight_pct: float | None
    isin: str | None
    boursorama_ticker: str | None


class GetEtfCompositionOutput(BaseModel):
    index_id: UUID | None
    boursorama_ticker: str
    composition_url: str
    holdings: list[EtfHoldingItem]
    fetched_at: datetime


class UpdateIndexBoursoramaInput(BaseModel):
    index_id: UUID
    boursorama_ticker: str = Field(min_length=1, max_length=32)


class UpdateIndexBoursoramaOutput(BaseModel):
    index_id: UUID
    name: str
    isin: str
    index_type: IndexType
    boursorama_ticker: str


class YahooIdentityInput(BaseModel):
    index_id: UUID | None = None
    isin: str | None = None
    yahoo_symbol: str | None = None

    @model_validator(mode="after")
    def exactly_one_key(self) -> "YahooIdentityInput":
        keys = [
            self.index_id is not None,
            self.isin is not None,
            self.yahoo_symbol is not None,
        ]
        if sum(keys) != 1:
            msg = "Exactly one of index_id, isin, or yahoo_symbol must be provided"
            raise ValueError(msg)
        return self


class GetAssetPriceFromYfInput(YahooIdentityInput):
    pass


class GetAssetPriceFromYfOutput(BaseModel):
    yahoo_symbol: str
    currency: str | None
    last_price: Decimal | None
    previous_close: Decimal | None
    fetched_at: datetime
    resolved_from_db: bool


class GetAssetHistoryFromYfInput(YahooIdentityInput):
    period: str = Field(default="1y", pattern=r"^(1mo|3mo|6mo|1y|5y|max)$")
    interval: str = Field(default="1d")


class HistoryBar(BaseModel):
    date: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None


class GetAssetHistoryFromYfOutput(BaseModel):
    yahoo_symbol: str
    period: str
    interval: str
    bars: list[HistoryBar]
    count: int
    resolved_from_db: bool


class GetCompanyFinancialsFromYfInput(YahooIdentityInput):
    include_statements: bool = True


class GetCompanyFinancialsFromYfOutput(BaseModel):
    yahoo_symbol: str
    index_type: IndexType
    info: dict[str, object]
    income_statement: list[dict[str, object]] | None = None
    balance_sheet: list[dict[str, object]] | None = None
    cash_flow: list[dict[str, object]] | None = None
    fetched_at: datetime
    resolved_from_db: bool


class GetAssetNewsFromYfInput(YahooIdentityInput):
    limit: int = Field(default=10, ge=1, le=25)


class YahooNewsItem(BaseModel):
    title: str
    link: str
    publisher: str | None
    published_at: datetime | None


class GetAssetNewsFromYfOutput(BaseModel):
    yahoo_symbol: str
    items: list[YahooNewsItem]
    count: int
    resolved_from_db: bool


class SearchYahooSymbolInput(BaseModel):
    query: str | None = None
    isin: str | None = None
    index_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one_key(self) -> "SearchYahooSymbolInput":
        keys = [self.query is not None, self.isin is not None, self.index_id is not None]
        if sum(keys) != 1:
            msg = "Exactly one of query, isin, or index_id must be provided"
            raise ValueError(msg)
        return self


class SearchYahooSymbolOutput(BaseModel):
    yahoo_symbol: str
    name: str
    isin: str | None
    index_id: UUID | None
    index_type: IndexType
    exchange: str | None
    quote_type: str | None
    resolved_from_db: bool


class UpdateIndexYahooSymbolInput(BaseModel):
    index_id: UUID
    yahoo_symbol: str = Field(min_length=1, max_length=32)


class UpdateIndexYahooSymbolOutput(BaseModel):
    index_id: UUID
    name: str
    isin: str
    index_type: IndexType
    yahoo_symbol: str
