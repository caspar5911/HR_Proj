import uuid
from datetime import datetime, timezone


def generate_token() -> str:
    """Generate a secure random token."""
    return uuid.uuid4().hex


def utcnow() -> datetime:
    """Return current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)