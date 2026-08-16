"""The seed script must not leak the superadmin password into stdout.

Logs, deploy output, and screenshots all inherit whatever the seed step
prints, so the password — even a strong one — must never appear there.
"""

from app.config import settings
from scripts.seed import seed


async def test_seed_does_not_print_admin_password(db, monkeypatch, capsys):
    fake_password = "S3cr3t-P@ssw0rd-XYZ"
    monkeypatch.setattr(settings, "SEED_ADMIN_EMAIL", "boss@example.org")
    monkeypatch.setattr(settings, "SEED_ADMIN_PASSWORD", fake_password)

    await seed(db)

    out = capsys.readouterr().out
    assert fake_password not in out
    # The email is fine to print — it is not a secret.
    assert "boss@example.org" in out
