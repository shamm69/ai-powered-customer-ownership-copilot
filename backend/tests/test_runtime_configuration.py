"""Tests for small environment-driven deployment configuration."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.runtime_configuration import (
    ALLOWED_FRONTEND_ORIGINS_ENVIRONMENT_VARIABLE,
    BACKEND_DIRECTORY,
    DATABASE_PATH_ENVIRONMENT_VARIABLE,
    DEFAULT_ALLOWED_FRONTEND_ORIGINS,
    DEFAULT_DATABASE_PATH,
    DEFAULT_PREDICTIVE_ARTIFACT_DIRECTORY,
    PREDICTIVE_ARTIFACT_DIRECTORY_ENVIRONMENT_VARIABLE,
    configure_cors,
    get_allowed_frontend_origins,
    get_database_path,
    get_predictive_artifact_directory,
)


def test_runtime_path_configuration_defaults_are_module_anchored() -> None:
    assert get_database_path({}) == DEFAULT_DATABASE_PATH
    assert get_predictive_artifact_directory({}) == (
        DEFAULT_PREDICTIVE_ARTIFACT_DIRECTORY
    )
    assert DEFAULT_DATABASE_PATH == BACKEND_DIRECTORY / "customer_ownership.db"


def test_relative_runtime_paths_are_anchored_to_backend_directory() -> None:
    environment = {
        DATABASE_PATH_ENVIRONMENT_VARIABLE: "runtime/demo.db",
        PREDICTIVE_ARTIFACT_DIRECTORY_ENVIRONMENT_VARIABLE: (
            "runtime/predictive"
        ),
    }

    assert get_database_path(environment) == (
        BACKEND_DIRECTORY / "runtime" / "demo.db"
    ).resolve()
    assert get_predictive_artifact_directory(environment) == (
        BACKEND_DIRECTORY / "runtime" / "predictive"
    ).resolve()


def test_cors_configuration_uses_safe_local_defaults() -> None:
    assert get_allowed_frontend_origins({}) == DEFAULT_ALLOWED_FRONTEND_ORIGINS
    assert "*" not in DEFAULT_ALLOWED_FRONTEND_ORIGINS


def test_cors_configuration_parses_exact_deduplicated_origins() -> None:
    environment = {
        ALLOWED_FRONTEND_ORIGINS_ENVIRONMENT_VARIABLE: (
            "https://ownership.example, https://manager.example/, "
            "https://ownership.example"
        )
    }

    assert get_allowed_frontend_origins(environment) == (
        "https://ownership.example",
        "https://manager.example",
    )


@pytest.mark.parametrize(
    "configured_origin",
    [
        "*",
        "ftp://ownership.example",
        "https://ownership.example/path",
        "https://user:secret@ownership.example",
    ],
)
def test_cors_configuration_rejects_unsafe_or_non_origin_values(
    configured_origin: str,
) -> None:
    with pytest.raises(ValueError, match="origin"):
        get_allowed_frontend_origins(
            {
                ALLOWED_FRONTEND_ORIGINS_ENVIRONMENT_VARIABLE: (
                    configured_origin
                )
            }
        )


def test_configured_cors_allows_only_the_exact_frontend_origin() -> None:
    application = FastAPI()
    configure_cors(application, ("https://ownership.example",))

    @application.post("/assistant/query")
    def assistant_query() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(application) as client:
        allowed = client.options(
            "/assistant/query",
            headers={
                "Origin": "https://ownership.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        denied = client.options(
            "/assistant/query",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == (
        "https://ownership.example"
    )
    assert "access-control-allow-credentials" not in allowed.headers
    assert "access-control-allow-origin" not in denied.headers


def test_configured_absolute_database_path_is_preserved(tmp_path: Path) -> None:
    configured_path = tmp_path / "data" / "application.db"

    assert get_database_path(
        {DATABASE_PATH_ENVIRONMENT_VARIABLE: str(configured_path)}
    ) == configured_path.resolve()
