class BoursoramaError(Exception):
    """Base error for Boursorama client and parsers."""


class BoursoramaRateLimitError(BoursoramaError):
    """Raised when rolling request budgets are exceeded."""


class BoursoramaUrlError(BoursoramaError):
    """Raised when a URL is outside the allowed host/path whitelist."""


class BoursoramaParseError(BoursoramaError):
    """Raised when HTML parsing yields no usable content."""
