"""Tests for proxy-aware client-IP resolution in the rate limiter."""

from types import SimpleNamespace

from app.config import settings
from app.middleware.rate_limit import client_ip


def _request(xff: str | None, host: str = "10.0.0.1") -> SimpleNamespace:
    """A minimal Request stand-in exposing just what client_ip reads."""
    headers = {"x-forwarded-for": xff} if xff else {}
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=host))


def test_client_ip_uses_first_xff_hop_when_trusted(monkeypatch):
    """Behind a trusted proxy the original client IP (first XFF hop) is used."""
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert client_ip(_request("203.0.113.7, 10.0.0.1")) == "203.0.113.7"


def test_client_ip_ignores_xff_when_untrusted(monkeypatch):
    """By default the XFF header is ignored — only the socket peer is used."""
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", False)
    assert client_ip(_request("203.0.113.7")) == "10.0.0.1"


def test_client_ip_falls_back_to_socket_when_xff_missing(monkeypatch):
    """Trusted but no XFF header present (e.g. a direct connection)."""
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert client_ip(_request(None)) == "10.0.0.1"
