"""Defensive security headers added to every outgoing response.

These are hardening headers that a top-tier deployment sends on *every*
response, regardless of status or content type:

* ``X-Content-Type-Options: nosniff`` — stop the browser from reinterpreting
  a response's MIME type.
* ``X-Frame-Options: DENY`` and ``Content-Security-Policy: frame-ancestors 'none'``
  — the app must never be embedded in a frame (clickjacking defence); the CSP
  form is the modern successor, so both are sent for older and newer browsers.
* ``Referrer-Policy: strict-origin-when-cross-origin`` — don't leak the full
  request URL (path and query, which can carry tokens) to other origins.

Implemented as a pure ASGI middleware (rather than Starlette's
``BaseHTTPMiddleware``) so it wraps every message that flows through
``send`` — including responses produced by FastAPI's exception handlers —
with no response buffering side effects.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Headers applied to every HTTP response. Values are fixed defaults; adjust
# here if a deployment needs a different policy.
_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "frame-ancestors 'none'",
}


class SecurityHeadersMiddleware:
    """Add defensive security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Only HTTP requests carry responses with headers; let websockets and
        # lifespan events pass through untouched.
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers: list = message["headers"]
                existing = {name for name, _ in headers}
                for name, value in _SECURITY_HEADERS.items():
                    name_bytes = name.encode("latin-1")
                    if name_bytes not in existing:
                        headers.append((name_bytes, value.encode("latin-1")))
                        existing.add(name_bytes)
            await send(message)

        await self.app(scope, receive, send_with_headers)
