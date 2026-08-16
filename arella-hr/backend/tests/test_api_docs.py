"""The OpenAPI surface must not be publicly advertised by default.

A live Swagger UI + OpenAPI schema enumerates every endpoint, request
model and parameter — a ready-made attack map. Docs are only served when
EXPOSE_API_DOCS is explicitly enabled (the dev compose stack does this);
production deployments keep them off.

Each test builds its own app via ``create_app()`` with the setting
monkeypatched, so the outcome does not depend on the environment the
suite happens to run in.
"""

import httpx

from app.config import settings
from app.main import create_app


async def _get(app, url: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        return await c.get(url)


async def test_docs_hidden_by_default(monkeypatch):
    monkeypatch.setattr(settings, "EXPOSE_API_DOCS", False)
    app = create_app()

    for url in ("/api/docs", "/api/openapi.json", "/redoc"):
        assert (await _get(app, url)).status_code == 404, url

    # Only the docs surface is hidden — the app itself still serves traffic.
    assert (await _get(app, "/health")).status_code == 200


async def test_docs_served_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "EXPOSE_API_DOCS", True)
    app = create_app()

    assert (await _get(app, "/api/docs")).status_code == 200
    spec = (await _get(app, "/api/openapi.json")).json()
    assert spec["paths"]
