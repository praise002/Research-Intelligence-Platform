from src.exceptions import ARCIPError, NotFound


class CompetitorNotFound(NotFound):
    def __init__(self, message: str = "Competitor not found"):
        """Raised when a competitor doesn't exist, or exists but belongs to a different user"""
        self.message = message
        super().__init__(message)


class CompetitorAlreadyExists(ARCIPError):
    """Raised when the user already tracks a competitor with this exact name."""
    def __init__(self, message: str = "You're already tracking a competitor with this name"):
        self.message = message
        super().__init__(message)


class SourceDiscoveryFailed(ARCIPError):
    """
    Raised by service.save_discovered_sources() in the (rare) case where
    every step of the discovery chain — robots.txt/sitemap, llms.txt,
    AND the fixed fallback paths — produces zero usable URLs. Since
    fallback paths are hardcoded and always return something, this
    should only fire if discovered list itself was passed in empty due
    to a bug upstream, not from a real competitor lookup.
    """
    def __init__(self, message: str = "Could not discover any pages for this competitor"):
        self.message = message
        super().__init__(message)