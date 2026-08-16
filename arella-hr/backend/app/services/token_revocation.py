"""In-memory refresh-token revocation store.

Holds the ``jti`` (JWT id) of refresh tokens that have been revoked —
explicitly on logout, or implicitly on rotation (issuing a new pair revokes
the presented token). Entries are keyed by expiry and purged lazily on read,
so the store cannot grow past the set of live refresh tokens.

State is deliberately in-process, matching the rate limiters: fine for a
single-server deployment and easy to swap for Redis later. A process restart
clears the store — a *safe* failure mode, since at worst a revoked token
stays usable until it expires on its own.
"""

import time


class TokenRevocationStore:
    """Map of ``jti`` -> expiry (Unix epoch seconds) for revoked refresh tokens."""

    def __init__(self) -> None:
        self._revoked: dict[str, float] = {}

    def revoke(self, jti: str, exp_epoch: float) -> None:
        """Remember ``jti`` as revoked.

        The entry lives only as long as the token itself: once ``exp_epoch``
        has passed the token is unusable anyway, so there is nothing left to
        keep on record.
        """
        if exp_epoch <= time.time():
            return
        self._revoked[jti] = exp_epoch

    def is_revoked(self, jti: str | None) -> bool:
        """Return True when ``jti`` was revoked and has not yet expired."""
        if not jti:
            return False
        self._purge_expired()
        return jti in self._revoked

    def clear(self) -> None:
        """Drop every entry (used by the test suite for isolation)."""
        self._revoked.clear()

    def _purge_expired(self) -> None:
        now = time.time()
        stale = [jti for jti, exp in self._revoked.items() if exp <= now]
        for jti in stale:
            del self._revoked[jti]


# Module-level singleton — the endpoints and the tests share one store.
REVOKED_REFRESH_TOKENS = TokenRevocationStore()
