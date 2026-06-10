class YahooError(Exception):
    """Base error for Yahoo Finance integration."""


class YahooSymbolNotFoundError(YahooError):
    """No resolvable Yahoo symbol for the given query."""


class YahooDataUnavailableError(YahooError):
    """Yahoo returned no data for an otherwise valid symbol."""
