"""Audit logging service.

Call :func:`record_audit` from API endpoints after a successful
create/update/delete
so the change is captured in the audit trail. The helper is deliberately
forgiving: a failure to write an audit row must never break the primary
operation that succeeded.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.audit_log import AuditLog
from app.models.user import User


def diff_changes(old: dict[str, Any], new: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Build an ``{"old": ..., "new": ...}`` snapshot of the fields that changed.

    ``old`` is a snapshot of the record's current values and ``new`` the
    candidate values (typically ``payload.model_dump(exclude_unset=True)``).
    Returns ``None`` when nothing actually changed.
    """
    changed: dict[str, Any] = {}
    for key, value in new.items():
        if key in old and old[key] != value:
            changed[key] = value
    if not changed:
        return None
    return {"old": {k: old[k] for k in changed}, "new": changed}


def _json_safe(value: Any) -> Any:
    """Recursively coerce values that are not natively JSON-serialisable.

    ORM attributes read back from the database can carry ``Decimal`` (from
    ``Numeric`` columns) or ``date``/``datetime`` objects, which the JSON
    column serializer rejects.  Converting them up front keeps audit writes
    from failing — and, crucially, from rolling back the caller's session
    (a rollback would expire every instance in it).
    """
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):  # also covers datetime (subclass of date)
        return value.isoformat()
    return value


async def record_audit(
    db: AsyncSession,
    *,
    user: Optional[User],
    request: Optional[Request],
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    changes: Optional[dict[str, Any]] = None,
) -> Optional[AuditLog]:
    """Write one audit log entry.

    Args:
        db: active async session.
        user: the authenticated user, or ``None`` for system actions.
        request: the incoming request (used for IP + user agent); may be None.
        action: e.g. ``"employee.created"``.
        entity: e.g. ``"employee"``.
        entity_id: primary key of the affected record, when available.
        changes: JSON-serialisable snapshot (see model docstring for shape).

    Returns the persisted :class:`AuditLog`, or ``None`` if writing failed.
    """
    try:
        ip_address: Optional[str] = None
        user_agent: Optional[str] = None
        if request is not None:
            client = request.client
            if client is not None:
                ip_address = client.host
            user_agent = request.headers.get("user-agent")

        log = AuditLog(
            user_id=user.id if user is not None else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            changes=_json_safe(changes) if changes is not None else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log
    except Exception:
        # Never let an audit failure take down the request; roll back any
        # partial transaction state and swallow.
        try:
            await db.rollback()
        except Exception:
            pass
        return None
