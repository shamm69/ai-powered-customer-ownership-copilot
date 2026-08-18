"""Tests for deterministic fresh-runtime application preparation."""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from pytest import MonkeyPatch
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app import main as main_module
from app.models import Customer, ServiceRecord, Vehicle
from app.predictive_maintenance_artifact import (
    EXPERIMENTAL_DECISION_THRESHOLD,
    MODEL_ARTIFACT_FILENAME,
    METADATA_FILENAME,
    MVP_AUTHORITY_STATEMENT,
    prepare_experimental_maintenance_artifact,
)
from app.predictive_maintenance_data import (
    PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
)
from app.runtime_bootstrap import initialize_runtime


def create_runtime_database(
    database_path: Path,
) -> tuple[Engine, sessionmaker[Session]]:
    database_engine = create_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}"
    )
    return database_engine, sessionmaker(
        bind=database_engine,
        autoflush=False,
        expire_on_commit=False,
    )


def test_fresh_runtime_creates_and_idempotently_seeds_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "database" / "application.db"
    artifact_directory = tmp_path / "artifacts"
    database_engine, session_factory = create_runtime_database(database_path)

    first = initialize_runtime(
        database_engine=database_engine,
        session_factory=session_factory,
        database_path=database_path,
        artifact_directory=artifact_directory,
    )
    second = initialize_runtime(
        database_engine=database_engine,
        session_factory=session_factory,
        database_path=database_path,
        artifact_directory=artifact_directory,
    )

    assert first.database_seeded is True
    assert first.predictive_artifact_created is True
    assert second.database_seeded is False
    assert second.predictive_artifact_created is False
    assert database_path.is_file()
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Customer)) == 3
        assert session.scalar(select(func.count()).select_from(Vehicle)) == 4
        assert (
            session.scalar(select(func.count()).select_from(ServiceRecord))
            == 7
        )


def test_missing_artifact_is_reconstructed_with_frozen_contract(
    tmp_path: Path,
) -> None:
    preparation = prepare_experimental_maintenance_artifact(tmp_path)
    metadata = preparation.artifact.metadata
    pipeline = preparation.artifact.pipeline

    assert preparation.created is True
    assert (tmp_path / MODEL_ARTIFACT_FILENAME).is_file()
    assert (tmp_path / METADATA_FILENAME).is_file()
    assert isinstance(pipeline.named_steps["standard_scaler"], StandardScaler)
    assert isinstance(
        pipeline.named_steps["logistic_regression"],
        LogisticRegression,
    )
    assert metadata.feature_names == PREDICTIVE_MAINTENANCE_FEATURE_NAMES
    assert metadata.decision_threshold == EXPERIMENTAL_DECISION_THRESHOLD == 0.19
    assert metadata.useful_value_gate_passed is False
    assert metadata.experimental is True
    assert metadata.mvp_authority == MVP_AUTHORITY_STATEMENT


def test_existing_valid_artifact_is_reused_without_retraining(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    first = prepare_experimental_maintenance_artifact(tmp_path)

    def fail_if_retrained() -> None:
        raise AssertionError("A valid artifact must not be retrained")

    monkeypatch.setattr(
        "app.predictive_maintenance_artifact."
        "build_default_experimental_maintenance_artifact",
        fail_if_retrained,
    )
    second = prepare_experimental_maintenance_artifact(tmp_path)

    assert first.created is True
    assert second.created is False
    assert second.artifact.metadata == first.artifact.metadata


def test_partial_artifact_pair_fails_clearly_instead_of_overwriting(
    tmp_path: Path,
) -> None:
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / METADATA_FILENAME).write_text("{}", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Model artifact not found"):
        prepare_experimental_maintenance_artifact(tmp_path)


def test_application_lifespan_runs_runtime_initialization(
    monkeypatch: MonkeyPatch,
) -> None:
    initialization_calls: list[str] = []
    monkeypatch.setattr(
        main_module,
        "initialize_runtime",
        lambda: initialization_calls.append("initialized"),
    )

    with TestClient(main_module.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert initialization_calls == ["initialized"]


def test_application_startup_does_not_swallow_initialization_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    def fail_initialization() -> None:
        raise RuntimeError("runtime initialization failed")

    monkeypatch.setattr(main_module, "initialize_runtime", fail_initialization)

    with pytest.raises(RuntimeError, match="runtime initialization failed"):
        with TestClient(main_module.app):
            pass
