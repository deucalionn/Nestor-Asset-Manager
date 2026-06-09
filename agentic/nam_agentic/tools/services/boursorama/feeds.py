from dataclasses import dataclass

from nam_db.enums import NewsCategory

BOURSORAMA_BASE = "https://www.boursorama.com"


@dataclass(frozen=True)
class IngestFeed:
    path: str
    category: NewsCategory

    @property
    def url(self) -> str:
        return f"{BOURSORAMA_BASE}{self.path}"


DAILY_FEEDS: tuple[IngestFeed, ...] = (
    IngestFeed("/bourse/actualites/calendriers/", NewsCategory.CALENDAR_GENERAL),
    IngestFeed(
        "/bourse/actualites/calendriers/societes-cotees",
        NewsCategory.CALENDAR_LISTED_COMPANIES,
    ),
    IngestFeed(
        "/bourse/actualites/calendriers/macroeconomique",
        NewsCategory.CALENDAR_MACRO,
    ),
    IngestFeed(
        "/bourse/actualites/calendriers/dividendes",
        NewsCategory.CALENDAR_DIVIDENDS,
    ),
)

SESSION_FEEDS: tuple[IngestFeed, ...] = (
    IngestFeed("/bourse/actualites/marches/", NewsCategory.MARKETS),
    IngestFeed("/bourse/actualites/finances/", NewsCategory.FINANCE),
)
