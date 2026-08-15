"""Structured error handling.

Defines a family of application exceptions that carry a machine-readable
``code`` plus a human-readable ``message``, and the FastAPI exception
handlers that render them as::

    {"detail": {"code": "NOT_FOUND", "message": "..."}}

Every error response in the API — including raw ``HTTPException`` raises and
Pydantic validation failures — is given a machine-readable ``code`` so that
clients can branch on it without parsing the human message.
"""

from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


# ── exception hierarchy ─────────────────────────────────────────────────────


class AppException(Exception):
    """Base class for all application-level errors.

    Attributes:
        code: machine-readable error code (e.g. ``"NOT_FOUND"``).
        message: human-readable message.
        status_code: HTTP status code to respond with.
        details: optional extra structured payload, sent as ``detail.details``.
    """

    code: str = "APP_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str = "",
        *,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.code
        if status_code is not None:
            self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ValidationError(AppException):
    """Client sent bad input or violated a business rule (400)."""

    code = "VALIDATION_ERROR"
    status_code = 400


class NotFoundError(AppException):
    """The requested resource does not exist (404)."""

    code = "NOT_FOUND"
    status_code = 404


class PermissionDeniedError(AppException):
    """The user is authenticated but not allowed to perform the action (403)."""

    code = "PERMISSION_DENIED"
    status_code = 403


class InsufficientBalanceError(ValidationError):
    """A leave request exceeds the employee's remaining balance (400)."""

    code = "INSUFFICIENT_BALANCE"
    status_code = 400


class RateLimitError(AppException):
    """The client exceeded the allowed request rate for an endpoint (429)."""

    code = "RATE_LIMITED"
    status_code = 429


# ── status → code mapping (used for raw HTTPException) ──────────────────────

_STATUS_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
}


def code_for_status(status_code: int) -> str:
    """Return the machine-readable code for an HTTP status code."""
    return _STATUS_CODE_MAP.get(status_code, "ERROR")


# ── exception handlers ──────────────────────────────────────────────────────


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Render an :class:`AppException` as a structured error body."""
    body: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details is not None:
        body["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content={"detail": body})


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Render any FastAPI/Starlette ``HTTPException`` with a machine code."""
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    body = {"code": code_for_status(exc.status_code), "message": message}
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": body},
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Render Pydantic request-validation failures with a machine code."""
    body = {
        "code": "VALIDATION_ERROR",
        "message": "Request validation failed",
        "details": jsonable_encoder(exc.errors()),
    }
    return JSONResponse(status_code=422, content={"detail": body})


def register_exception_handlers(app) -> None:
    """Attach all structured-error handlers to a FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
