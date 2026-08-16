"""Settings must refuse to boot with an insecure JWT signing key.

Every access and refresh token is signed with ``SECRET_KEY``. If a
deployment were to run with the value that used to ship in this repo (or
with no key at all), anyone could forge tokens and impersonate any user,
so the settings layer fails fast at startup.
"""

import pytest

from app.config import Settings, _INSECURE_SECRET_KEY, _MIN_SECRET_KEY_LENGTH


def test_rejects_missing_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings()


def test_rejects_known_insecure_default(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", _INSECURE_SECRET_KEY)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings()


def test_rejects_short_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * (_MIN_SECRET_KEY_LENGTH - 1))
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings()


def test_accepts_strong_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "s" * 64)
    settings = Settings()
    assert settings.SECRET_KEY == "s" * 64
