"""Every response carries defensive security headers.

A real deployment must send these on *all* responses — successes, client
errors, and the error bodies produced by FastAPI's exception handlers — not
just the 200s. The middleware is a pure ASGI wrapper, so it catches responses
regardless of where in the stack they originate.
"""

import httpx

EXPECTED = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "frame-ancestors 'none'",
}


def assert_headers_present(response: httpx.Response) -> None:
    for name, value in EXPECTED.items():
        assert response.headers.get(name) == value, (
            f"missing/incorrect {name!r}: got {response.headers.get(name)!r}, "
            f"want {value!r}"
        )


async def test_success_response_has_security_headers(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert_headers_present(resp)


async def test_error_response_has_security_headers(client):
    """A 401 raised by the auth dependency (exception handler) still carries
    the headers — proving the middleware wraps responses from every layer."""
    resp = await client.get("/api/v1/auth/me")  # no token → 401
    assert resp.status_code == 401
    assert_headers_present(resp)
