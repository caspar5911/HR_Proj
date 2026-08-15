"""In-memory rate limiting for sensitive endpoints.

A sliding-window counter keyed by client IP. State is deliberately kept
in-process: fine for a single-server deployment, and easy to swap for
Redis later without touching the endpoint wiring.
"""

import time
from collections import defaultdict, deque

from fastapi import Request

from app.utils.errors import RateLimitError


class RateLimiter:
    """Sliding-window counter: at most ``max_requests`` per key per window."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        """Record a hit for ``key``; return ``False`` if the limit is exceeded."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        hits = self._hits[key]
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True


def client_ip(request: Request) -> str:
    """Best-effort client IP to use as the rate-limit key."""
    return request.client.host if request.client else "unknown"


# Per-endpoint limiters (per client IP, 5-minute sliding window).
LOGIN_LIMITER = RateLimiter(max_requests=10, window_seconds=300)
REFRESH_LIMITER = RateLimiter(max_requests=20, window_seconds=300)
# Reserved for a future /auth/register endpoint (5 / 5 min / IP).
REGISTER_LIMITER = RateLimiter(max_requests=5, window_seconds=300)


def limit_login(request: Request) -> None:
    """FastAPI dependency — enforce the login rate limit."""
    if not LOGIN_LIMITER.allow(client_ip(request)):
        raise RateLimitError("Too many login attempts. Try again later.")


def limit_refresh(request: Request) -> None:
    """FastAPI dependency — enforce the refresh-token rate limit."""
    if not REFRESH_LIMITER.allow(client_ip(request)):
        raise RateLimitError("Too many token refresh attempts. Try again later.")
