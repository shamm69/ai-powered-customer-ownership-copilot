"""Static checks for the production backend container contract."""

from pathlib import Path

from app.document_embeddings import DEFAULT_EMBEDDING_MODEL

BACKEND_DIRECTORY = Path(__file__).resolve().parent.parent
DOCKERFILE = BACKEND_DIRECTORY / "Dockerfile"
DOCKERIGNORE = BACKEND_DIRECTORY / ".dockerignore"
RUNTIME_REQUIREMENTS = BACKEND_DIRECTORY / "requirements-runtime.txt"
DEVELOPMENT_REQUIREMENTS = BACKEND_DIRECTORY / "requirements.txt"


def test_runtime_requirements_exclude_test_only_dependencies() -> None:
    runtime_requirements = RUNTIME_REQUIREMENTS.read_text(encoding="utf-8")
    development_requirements = DEVELOPMENT_REQUIREMENTS.read_text(
        encoding="utf-8"
    )

    assert "fastapi" in runtime_requirements
    assert "sentence-transformers" in runtime_requirements
    assert "pytest" not in runtime_requirements
    assert "httpx2" not in runtime_requirements
    assert "-r requirements-runtime.txt" in development_requirements


def test_dockerfile_uses_supported_python_and_production_server() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert dockerfile.startswith("FROM python:3.13-slim\n")
    assert "uvicorn app.main:app" in dockerfile
    assert "--host 0.0.0.0" in dockerfile
    assert "${PORT:-8000}" in dockerfile
    assert "--reload" not in dockerfile


def test_dockerfile_prefetches_the_exact_existing_embedding_model() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert DEFAULT_EMBEDDING_MODEL in dockerfile
    assert "HF_HUB_OFFLINE=1" in dockerfile
    assert "TRANSFORMERS_OFFLINE=1" in dockerfile


def test_dockerfile_preserves_runtime_bootstrap_paths() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert (
        "CUSTOMER_OWNERSHIP_DATABASE_PATH="
        "/app/runtime/customer_ownership.db" in dockerfile
    )
    assert (
        "PREDICTIVE_MAINTENANCE_ARTIFACT_DIRECTORY="
        "/app/runtime/predictive_maintenance" in dockerfile
    )
    assert "COPY --chown=app:app app ./app" in dockerfile
    assert "COPY --chown=app:app knowledge ./knowledge" in dockerfile


def test_dockerfile_runs_as_non_root_and_has_a_healthcheck() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "USER app" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/health" in dockerfile


def test_dockerfile_does_not_embed_secret_configuration() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "GEMINI_API_KEY=" not in dockerfile
    assert "ARG GEMINI_API_KEY" not in dockerfile
    assert "COPY .env" not in dockerfile


def test_dockerignore_excludes_local_and_generated_state() -> None:
    ignored_entries = set(
        DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
    )

    assert {
        ".git",
        ".env",
        ".env.*",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        "tests",
        "customer_ownership.db",
        "artifacts",
        "*.joblib",
        "*.pkl",
    } <= ignored_entries


def test_dockerignore_keeps_required_application_resources() -> None:
    ignored_entries = set(
        DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
    )

    assert "app" not in ignored_entries
    assert "knowledge" not in ignored_entries
    assert "requirements-runtime.txt" not in ignored_entries
