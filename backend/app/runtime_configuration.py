"""Small environment-driven configuration boundary for runtime deployment."""

from collections.abc import Mapping
import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.observability import REQUEST_ID_HEADER

BACKEND_DIRECTORY = Path(__file__).resolve().parent.parent

DATABASE_PATH_ENVIRONMENT_VARIABLE = "CUSTOMER_OWNERSHIP_DATABASE_PATH"
PREDICTIVE_ARTIFACT_DIRECTORY_ENVIRONMENT_VARIABLE = (
    "PREDICTIVE_MAINTENANCE_ARTIFACT_DIRECTORY"
)
ALLOWED_FRONTEND_ORIGINS_ENVIRONMENT_VARIABLE = "ALLOWED_FRONTEND_ORIGINS"

DEFAULT_DATABASE_PATH = BACKEND_DIRECTORY / "customer_ownership.db"
DEFAULT_PREDICTIVE_ARTIFACT_DIRECTORY = (
    BACKEND_DIRECTORY / "artifacts" / "predictive_maintenance"
)
DEFAULT_ALLOWED_FRONTEND_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


def get_database_path(
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Return the configured SQLite path, anchored predictably when relative."""
    return _configured_path(
        DATABASE_PATH_ENVIRONMENT_VARIABLE,
        DEFAULT_DATABASE_PATH,
        environment,
    )


def get_predictive_artifact_directory(
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Return the configured generated-artifact directory."""
    return _configured_path(
        PREDICTIVE_ARTIFACT_DIRECTORY_ENVIRONMENT_VARIABLE,
        DEFAULT_PREDICTIVE_ARTIFACT_DIRECTORY,
        environment,
    )


def get_allowed_frontend_origins(
    environment: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Parse exact allowed frontend origins with safe local defaults."""
    values = os.environ if environment is None else environment
    configured = values.get(ALLOWED_FRONTEND_ORIGINS_ENVIRONMENT_VARIABLE)
    if configured is None or not configured.strip():
        return DEFAULT_ALLOWED_FRONTEND_ORIGINS

    origins = tuple(
        dict.fromkeys(
            origin.strip().rstrip("/")
            for origin in configured.split(",")
            if origin.strip()
        )
    )
    if not origins:
        raise ValueError("At least one allowed frontend origin is required")
    for origin in origins:
        _validate_origin(origin)
    return origins


def configure_cors(
    application: FastAPI,
    origins: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """Add the exact CORS policy required by the browser frontend."""
    allowed_origins = (
        get_allowed_frontend_origins() if origins is None else origins
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    return allowed_origins


def _configured_path(
    name: str,
    default: Path,
    environment: Mapping[str, str] | None,
) -> Path:
    values = os.environ if environment is None else environment
    configured = values.get(name)
    if configured is None or not configured.strip():
        return default

    path = Path(configured.strip()).expanduser()
    if not path.is_absolute():
        path = BACKEND_DIRECTORY / path
    return path.resolve()


def _validate_origin(origin: str) -> None:
    if origin == "*":
        raise ValueError("Wildcard CORS origins are not allowed")
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Allowed frontend origins must be exact HTTP(S) origins"
        )
