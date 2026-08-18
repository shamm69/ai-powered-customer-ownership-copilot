"""Explicit startup preparation for a fresh application runtime."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, DATABASE_PATH, SessionLocal, engine
from app.predictive_maintenance_artifact import (
    ExperimentalArtifactPreparation,
    prepare_experimental_maintenance_artifact,
)
from app.runtime_configuration import get_predictive_artifact_directory
from app.seed import seed_database


@dataclass(frozen=True)
class RuntimeBootstrapResult:
    """Observable outcome of deterministic runtime preparation."""

    database_seeded: bool
    predictive_artifact_created: bool


def initialize_runtime_database(
    database_engine: Engine,
    session_factory: sessionmaker[Session],
) -> bool:
    """Create missing tables and idempotently apply the existing demo seed."""
    Base.metadata.create_all(database_engine)
    with session_factory() as session:
        return seed_database(session)


def initialize_runtime(
    *,
    database_engine: Engine = engine,
    session_factory: sessionmaker[Session] = SessionLocal,
    database_path: Path = DATABASE_PATH,
    artifact_directory: Path | None = None,
) -> RuntimeBootstrapResult:
    """Prepare the database and frozen experimental artifact or fail clearly."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_seeded = initialize_runtime_database(
        database_engine,
        session_factory,
    )
    artifact_preparation: ExperimentalArtifactPreparation = (
        prepare_experimental_maintenance_artifact(
            artifact_directory or get_predictive_artifact_directory()
        )
    )
    return RuntimeBootstrapResult(
        database_seeded=database_seeded,
        predictive_artifact_created=artifact_preparation.created,
    )
