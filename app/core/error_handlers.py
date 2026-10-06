"""Global FastAPI exception handlers.

Centralizes translation of exceptions into a consistent JSON error envelope
(`{"detail": ..., "type": ...}`) so route handlers do not need to format
error responses by hand. Register with `register_exception_handlers(app)`
during application startup.

The handler set covers both exception roots of the codebase: the API-facing
`BaseAppException` tree and the agent engine `AgentEngineError` tree, plus
framework (HTTPException / RequestValidationError) and persistence
(IntegrityError) failures.
"""

from __future__ import annotations

import re

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AgentEngineError, BaseAppException
from app.core.logging_setup import write_crash_dump

logger = structlog.get_logger(__name__)

_NOT_NULL_PATTERN = re.compile(r"not[\s-]?null", re.IGNORECASE)
_CHECK_PATTERN = re.compile(r"check constraint", re.IGNORECASE)
_UNIQUE_PATTERN = re.compile(r"unique constraint|duplicate key", re.IGNORECASE)
_FOREIGN_KEY_PATTERN = re.compile(r"foreign key", re.IGNORECASE)
_CONSTRAINT_NAME_PATTERN = re.compile(r"constraint \"?([\w.$-]+)\"")
_COLUMNS_PATTERN = re.compile(r"constraint failed: (.+)$", re.IGNORECASE)
_QUOTED_COLUMN_PATTERN = re.compile(r"column \"([\w.$-]+)\"")

# Constraint classification: (status_code, error_type, client-safe detail).
_NOT_NULL_RESPONSE = (422, "integrity_constraint", "A required field is missing or null")
_CHECK_RESPONSE = (422, "integrity_constraint", "A field value failed a database constraint")
_FOREIGN_KEY_RESPONSE = (422, "integrity_constraint", "A referenced record is missing or invalid")
_UNIQUE_RESPONSE = (409, "integrity_conflict", "A record with the same unique value already exists")
_PERSISTENCE_RESPONSE = (500, "persistence_error", "The request could not be persisted")


def _error_body(detail: str, error_type: str) -> dict[str, str]:
    """Build the standard error response body.

    Args:
        detail: Human-readable error message.
        error_type: Machine-readable error category.

    Returns:
        A dictionary with `detail` and `type` keys.
    """
    return {"detail": detail, "type": error_type}


def _classify_integrity_error(orig: BaseException | None) -> tuple[int, str, str]:
    """Map the raw database constraint error to an HTTP classification.

    Not all integrity violations mean "conflict": NOT NULL and CHECK failures
    describe malformed input (422 `integrity_constraint`), unique violations
    describe conflicting state (409 `integrity_conflict`), and anything
    unrecognizable is reported as a persistence failure (500
    `persistence_error`) instead of guessing a conflict.

    Args:
        orig: The original driver-level exception attached to the
            SQLAlchemy IntegrityError.

    Returns:
        A tuple of (status_code, error_type, client-safe detail message).
    """
    message = str(orig) if orig else ""
    if _NOT_NULL_PATTERN.search(message):
        return _NOT_NULL_RESPONSE
    if _CHECK_PATTERN.search(message):
        return _CHECK_RESPONSE
    if _UNIQUE_PATTERN.search(message):
        return _UNIQUE_RESPONSE
    if _FOREIGN_KEY_PATTERN.search(message):
        return _FOREIGN_KEY_RESPONSE
    return _PERSISTENCE_RESPONSE


def _describe_integrity_constraint(orig: BaseException | None) -> str:
    """Extract constraint or column identifiers from the raw database error.

    Used for diagnosis only; identifiers are kept in logs and stay out of
    the response body.

    Args:
        orig: The original driver-level exception attached to the
            SQLAlchemy IntegrityError.

    Returns:
        A short constraint identifier, or the raw message when no
        structured identifier can be extracted.
    """
    if orig is None:
        return "unknown"
    message = str(orig)
    name_match = _CONSTRAINT_NAME_PATTERN.search(message)
    if name_match:
        return name_match.group(1)
    columns_match = _COLUMNS_PATTERN.search(message)
    if columns_match:
        return columns_match.group(1).strip()
    column_match = _QUOTED_COLUMN_PATTERN.search(message)
    if column_match:
        return column_match.group(1)
    return message.strip() or "unknown"


async def handle_app_exception(request: Request, exc: BaseAppException) -> JSONResponse:
    """Translate a BaseAppException subclass into a JSON response.

    Args:
        request: The incoming FastAPI request.
        exc: The raised application exception.

    Returns:
        A JSONResponse using the exception's status_code and error_type.
    """
    del request
    return JSONResponse(status_code=exc.status_code, content=_error_body(exc.detail, exc.error_type))


async def handle_agent_engine_error(request: Request, exc: AgentEngineError) -> JSONResponse:
    """Map engine-tree errors surfacing at the API boundary to the envelope.

    Provides the reusable bridge between the agent engine exception tree
    (`AgentEngineError`) and the API error envelope: uncaught engine errors
    resolve to a structured 500 `agent_engine_error` response instead of an
    incidental unhandled traceback. The `AgentEngineHTTPError` subclass
    carries both roots and reaches this classification through either
    handler.

    Args:
        request: The incoming FastAPI request.
        exc: The uncaught agent engine error.

    Returns:
        A 500 JSONResponse with the agent_engine_error envelope.
    """
    logger.error(
        "Agent engine error surfaced at API boundary",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )
    return JSONResponse(status_code=500, content=_error_body("Agent engine failure", "agent_engine_error"))


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Translate a FastAPI/Starlette HTTPException into a JSON response.

    Args:
        request: The incoming FastAPI request.
        exc: The raised HTTP exception.

    Returns:
        A JSONResponse using the exception's status_code, preserving
        `exc.headers` (e.g. the Cache-Control: no-store header that
        model_discovery sets on credential errors).
    """
    del request
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": "http_error"},
        headers=exc.headers,
    )


async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Translate a request validation failure into a 422 JSON response.

    Args:
        request: The incoming FastAPI request.
        exc: The raised request validation error.

    Returns:
        A JSONResponse with the validation details and a consistent error type.
    """
    del request
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "type": "validation_error"},
    )


async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    """Translate a database integrity violation into an interpretable response.

    The constraint kind decides the classification: input-shaped violations
    (NOT NULL, CHECK, foreign key) return 422 `integrity_constraint`, unique
    conflicts keep 409 `integrity_conflict`, and anything unrecognizable
    becomes a 500 `persistence_error`. Constraint names and the raw driver
    error are kept in the log for diagnosis and stay out of the response
    body.

    Args:
        request: The incoming FastAPI request.
        exc: The raised SQLAlchemy integrity error.

    Returns:
        A JSONResponse classified by constraint type.
    """
    orig = exc.orig
    status_code, error_type, detail = _classify_integrity_error(orig)
    logger.warning(
        "Database integrity constraint rejected request",
        path=request.url.path,
        error_type=error_type,
        status_code=status_code,
        constraint=_describe_integrity_constraint(orig),
        original_error=str(orig) if orig else str(exc),
    )
    return JSONResponse(status_code=status_code, content=_error_body(detail, error_type))


async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for exceptions not covered by a specific handler.

    Writes a crash dump for post-mortem debugging and returns a generic
    500 response without leaking internal error details to the client.

    Args:
        request: The incoming FastAPI request.
        exc: The unhandled exception.

    Returns:
        A 500 JSONResponse with a generic error message.
    """
    dump = write_crash_dump(exc, {"path": request.url.path, "method": request.method})
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        crash_dump=str(dump) if dump else None,
        exc_info=True,
    )
    return JSONResponse(status_code=500, content=_error_body("Internal server error", "internal_error"))


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the given FastAPI app.

    Registration covers both exception roots: `BaseAppException` for the
    API tree and `AgentEngineError` as the bridge for the engine tree, so
    neither root can bypass the shared error envelope.

    Args:
        app: The FastAPI application instance to register handlers on.
    """
    app.add_exception_handler(BaseAppException, handle_app_exception)
    app.add_exception_handler(AgentEngineError, handle_agent_engine_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(IntegrityError, handle_integrity_error)
    app.add_exception_handler(Exception, handle_unhandled_exception)
