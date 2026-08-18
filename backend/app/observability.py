"""Lightweight structured logging for application and request operations."""

from collections.abc import Mapping
from datetime import UTC, datetime
import json
import logging
import os
import re
import sys
from time import perf_counter
from typing import TextIO
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

APPLICATION_LOGGER_NAME = "customer_ownership_copilot"
LOG_LEVEL_ENVIRONMENT_VARIABLE = "LOG_LEVEL"
DEFAULT_LOG_LEVEL = logging.INFO
REQUEST_ID_HEADER = "X-Request-ID"

_SUPPORTED_LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_STRUCTURED_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "routed_intent",
    "invoked_capability",
    "outcome",
    "context_missing",
    "database_seeded",
    "predictive_artifact_created",
    "exception_type",
)


class JsonLogFormatter(logging.Formatter):
    """Serialize the small approved operational field set as one JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        for field in _STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def resolve_log_level(
    environment: Mapping[str, str] | None = None,
) -> tuple[int, bool]:
    """Return a supported level and whether an invalid value used the fallback."""
    values = os.environ if environment is None else environment
    configured = values.get(LOG_LEVEL_ENVIRONMENT_VARIABLE, "INFO").strip().upper()
    level = _SUPPORTED_LOG_LEVELS.get(configured)
    if level is None:
        return DEFAULT_LOG_LEVEL, True
    return level, False


def configure_application_logging(
    environment: Mapping[str, str] | None = None,
    *,
    logger_name: str = APPLICATION_LOGGER_NAME,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure one application logger without replacing Uvicorn loggers."""
    logger = logging.getLogger(logger_name)
    level, used_fallback = resolve_log_level(environment)
    logger.setLevel(level)
    logger.propagate = False

    for handler in tuple(logger.handlers):
        if getattr(handler, "ownership_observability_handler", False):
            logger.removeHandler(handler)

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonLogFormatter())
    handler.ownership_observability_handler = True  # type: ignore[attr-defined]
    logger.addHandler(handler)

    if used_fallback:
        logger.warning(
            "invalid_log_level_fallback",
            extra={"event": "invalid_log_level_fallback"},
        )
    return logger


def select_request_id(inbound_value: str | None) -> str:
    """Reuse a simple safe inbound ID or generate an opaque UUID."""
    candidate = inbound_value.strip() if inbound_value is not None else ""
    if candidate and _SAFE_REQUEST_ID.fullmatch(candidate):
        return candidate
    return str(uuid4())


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """Add request IDs and structured request start/completion/error events."""

    def __init__(self, app: ASGIApp, *, logger: logging.Logger) -> None:
        super().__init__(app)
        self._logger = logger

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = select_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        method = request.method
        path = request.url.path
        started_at = perf_counter()
        self._logger.info(
            "request_started",
            extra={
                "event": "request_started",
                "request_id": request_id,
                "method": method,
                "path": path,
            },
        )
        try:
            response = await call_next(request)
        except Exception as exc:
            self._logger.error(
                "request_failed",
                extra={
                    "event": "request_failed",
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": _duration_ms(started_at),
                    "exception_type": type(exc).__name__,
                },
            )
            raise

        response.headers[REQUEST_ID_HEADER] = request_id
        self._logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": _duration_ms(started_at),
            },
        )
        return response


def _duration_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)
