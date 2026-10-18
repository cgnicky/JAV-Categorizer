class RateLimitedError(Exception):
    """JavLibrary throttled the request; safe to retry later."""


class SearchStoppedError(Exception):
    """User stopped the task or the browser window was closed."""
