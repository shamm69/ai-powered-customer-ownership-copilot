"""Tests for the experimental maintenance model artifact."""

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path

import joblib
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.predictive_maintenance_artifact import (
    ARTIFACT_SCHEMA_VERSION,
    EXPERIMENTAL_DECISION_THRESHOLD,
    MODEL_ARTIFACT_FILENAME,
    METADATA_FILENAME,
    MVP_AUTHORITY_STATEMENT,
    ExperimentalArtifactCompatibilityError,
    ExperimentalMaintenanceArtifact,
    build_default_experimental_maintenance_artifact,
    load_experimental_maintenance_artifact,
    save_experimental_maintenance_artifact,
    train_experimental_maintenance_artifact,
)
from app.predictive_maintenance_data import (
    DEFAULT_RANDOM_SEED,
    DEFAULT_SNAPSHOT_COUNT,
    PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
    PredictiveMaintenanceSnapshot,
    generate_predictive_maintenance_snapshots,
)
from app.predictive_maintenance_model import (
    DEFAULT_MODEL_RANDOM_SEED,
    DEFAULT_SPLIT_RANDOM_SEED,
    build_predictive_maintenance_feature_matrix,
    split_predictive_maintenance_snapshots,
)


@pytest.fixture(scope="module")
def snapshots() -> tuple[PredictiveMaintenanceSnapshot, ...]:
    return generate_predictive_maintenance_snapshots()


@pytest.fixture(scope="module")
def artifact() -> ExperimentalMaintenanceArtifact:
    return build_default_experimental_maintenance_artifact()


def test_artifact_creation_uses_only_established_training_partition(
    artifact: ExperimentalMaintenanceArtifact,
) -> None:
    scaler = artifact.pipeline.named_steps["standard_scaler"]

    assert scaler.n_samples_seen_ == 1_050
    assert artifact.metadata.dataset_size == DEFAULT_SNAPSHOT_COUNT
    assert artifact.metadata.training_row_count == 1_050
    assert artifact.metadata.validation_row_count == 225
    assert artifact.metadata.test_row_count == 225
    assert scaler.n_samples_seen_ != artifact.metadata.dataset_size


def test_saved_object_is_complete_fitted_pipeline(
    artifact: ExperimentalMaintenanceArtifact,
    tmp_path: Path,
) -> None:
    paths = save_experimental_maintenance_artifact(artifact, tmp_path)
    saved_pipeline = joblib.load(paths.model_path)

    assert isinstance(saved_pipeline, Pipeline)
    assert isinstance(saved_pipeline.named_steps["standard_scaler"], StandardScaler)
    assert isinstance(
        saved_pipeline.named_steps["logistic_regression"],
        LogisticRegression,
    )
    assert hasattr(saved_pipeline.named_steps["standard_scaler"], "mean_")
    assert hasattr(saved_pipeline.named_steps["logistic_regression"], "coef_")


def test_save_load_round_trip_preserves_probabilities(
    artifact: ExperimentalMaintenanceArtifact,
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
    tmp_path: Path,
) -> None:
    split = split_predictive_maintenance_snapshots(snapshots)
    features = build_predictive_maintenance_feature_matrix(split.validation[:10])
    expected_probabilities = artifact.pipeline.predict_proba(features)
    save_experimental_maintenance_artifact(artifact, tmp_path)

    loaded = load_experimental_maintenance_artifact(tmp_path)
    loaded_probabilities = loaded.pipeline.predict_proba(features)

    assert loaded_probabilities == pytest.approx(expected_probabilities)


def test_metadata_preserves_frozen_experiment_contract(
    artifact: ExperimentalMaintenanceArtifact,
) -> None:
    metadata = artifact.metadata

    assert metadata.schema_version == ARTIFACT_SCHEMA_VERSION
    assert metadata.feature_names == PREDICTIVE_MAINTENANCE_FEATURE_NAMES
    assert metadata.decision_threshold == EXPERIMENTAL_DECISION_THRESHOLD == 0.19
    assert metadata.experimental is True
    assert metadata.useful_value_gate_passed is False
    assert metadata.mvp_authority == MVP_AUTHORITY_STATEMENT
    assert metadata.dataset_random_seed == DEFAULT_RANDOM_SEED
    assert metadata.split_random_seed == DEFAULT_SPLIT_RANDOM_SEED
    assert metadata.model_random_seed == DEFAULT_MODEL_RANDOM_SEED


def test_threshold_validation_rejects_impossible_value(
    artifact: ExperimentalMaintenanceArtifact,
    tmp_path: Path,
) -> None:
    invalid_artifact = replace(
        artifact,
        metadata=replace(artifact.metadata, decision_threshold=1.5),
    )

    with pytest.raises(
        ExperimentalArtifactCompatibilityError,
        match="threshold",
    ):
        save_experimental_maintenance_artifact(invalid_artifact, tmp_path)


def test_incompatible_feature_order_is_rejected(
    artifact: ExperimentalMaintenanceArtifact,
    tmp_path: Path,
) -> None:
    paths = save_experimental_maintenance_artifact(artifact, tmp_path)
    metadata = json.loads(paths.metadata_path.read_text(encoding="utf-8"))
    metadata["feature_names"] = list(reversed(metadata["feature_names"]))
    paths.metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(
        ExperimentalArtifactCompatibilityError,
        match="feature ordering",
    ):
        load_experimental_maintenance_artifact(tmp_path)


def test_malformed_metadata_is_rejected(
    artifact: ExperimentalMaintenanceArtifact,
    tmp_path: Path,
) -> None:
    paths = save_experimental_maintenance_artifact(artifact, tmp_path)
    paths.metadata_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(
        ExperimentalArtifactCompatibilityError,
        match="valid readable JSON",
    ):
        load_experimental_maintenance_artifact(tmp_path)


@pytest.mark.parametrize(
    ("filename", "message"),
    [
        (MODEL_ARTIFACT_FILENAME, "Model artifact not found"),
        (METADATA_FILENAME, "Artifact metadata not found"),
    ],
)
def test_missing_artifact_files_fail_clearly(
    artifact: ExperimentalMaintenanceArtifact,
    tmp_path: Path,
    filename: str,
    message: str,
) -> None:
    paths = save_experimental_maintenance_artifact(artifact, tmp_path)
    path_to_remove = (
        paths.model_path
        if filename == MODEL_ARTIFACT_FILENAME
        else paths.metadata_path
    )
    path_to_remove.unlink()

    with pytest.raises(FileNotFoundError, match=message):
        load_experimental_maintenance_artifact(tmp_path)


def test_artifact_creation_does_not_mutate_input_data(
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
) -> None:
    original_snapshots = tuple(snapshots)

    train_experimental_maintenance_artifact(
        snapshots,
        dataset_random_seed=DEFAULT_RANDOM_SEED,
        split_random_seed=DEFAULT_SPLIT_RANDOM_SEED,
        model_random_seed=DEFAULT_MODEL_RANDOM_SEED,
    )

    assert snapshots == original_snapshots


def test_validation_and_test_rows_are_not_fitted(
    artifact: ExperimentalMaintenanceArtifact,
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
) -> None:
    split = split_predictive_maintenance_snapshots(snapshots)
    scaler = artifact.pipeline.named_steps["standard_scaler"]

    assert scaler.n_samples_seen_ == len(split.training)
    assert scaler.n_samples_seen_ != len(split.training) + len(split.validation)
    assert scaler.n_samples_seen_ != len(snapshots)


def test_generated_artifact_directory_is_ignored_by_git() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    gitignore = (repository_root / ".gitignore").read_text(encoding="utf-8")

    assert "backend/artifacts/predictive_maintenance/" in gitignore.splitlines()


def test_artifact_wrapper_and_metadata_are_immutable(
    artifact: ExperimentalMaintenanceArtifact,
) -> None:
    with pytest.raises(FrozenInstanceError):
        artifact.metadata = artifact.metadata  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        artifact.metadata.decision_threshold = 0.5  # type: ignore[misc]
