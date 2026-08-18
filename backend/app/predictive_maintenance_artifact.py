"""Persistence for the experimental predictive-maintenance model artifact."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from json import JSONDecodeError
import json
from math import isfinite
from pathlib import Path
from typing import Any

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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
    split_predictive_maintenance_snapshots,
    train_logistic_regression_model,
)

ARTIFACT_SCHEMA_VERSION = 1
EXPERIMENTAL_DECISION_THRESHOLD = 0.19
MODEL_FAMILY = "standard_scaler_logistic_regression_pipeline"
MVP_AUTHORITY_STATEMENT = (
    "The deterministic maintenance evaluator remains the authoritative MVP "
    "decision mechanism."
)
DEFAULT_ARTIFACT_DIRECTORY = (
    Path(__file__).resolve().parent.parent
    / "artifacts"
    / "predictive_maintenance"
)
MODEL_ARTIFACT_FILENAME = "experimental_maintenance_pipeline.joblib"
METADATA_FILENAME = "experimental_maintenance_metadata.json"


class ExperimentalArtifactCompatibilityError(ValueError):
    """Raised when saved artifact metadata or pipeline is incompatible."""


@dataclass(frozen=True)
class ExperimentalArtifactMetadata:
    """Transparent metadata required to interpret the fitted pipeline."""

    schema_version: int
    model_family: str
    feature_names: tuple[str, ...]
    decision_threshold: float
    dataset_size: int
    training_row_count: int
    validation_row_count: int
    test_row_count: int
    dataset_random_seed: int
    split_random_seed: int
    model_random_seed: int
    experimental: bool
    useful_value_gate_passed: bool
    mvp_authority: str

    def to_json_object(self) -> dict[str, object]:
        """Return a JSON-compatible representation with ordered features."""
        return {
            "schema_version": self.schema_version,
            "model_family": self.model_family,
            "feature_names": list(self.feature_names),
            "decision_threshold": self.decision_threshold,
            "dataset_size": self.dataset_size,
            "training_row_count": self.training_row_count,
            "validation_row_count": self.validation_row_count,
            "test_row_count": self.test_row_count,
            "dataset_random_seed": self.dataset_random_seed,
            "split_random_seed": self.split_random_seed,
            "model_random_seed": self.model_random_seed,
            "experimental": self.experimental,
            "useful_value_gate_passed": self.useful_value_gate_passed,
            "mvp_authority": self.mvp_authority,
        }


@dataclass(frozen=True)
class ExperimentalMaintenanceArtifact:
    """A fitted experimental pipeline paired with validated metadata."""

    pipeline: Pipeline
    metadata: ExperimentalArtifactMetadata


@dataclass(frozen=True)
class ExperimentalArtifactPaths:
    """Filesystem paths for one saved model and metadata pair."""

    model_path: Path
    metadata_path: Path


@dataclass(frozen=True)
class ExperimentalArtifactPreparation:
    """A validated artifact plus whether this operation reconstructed it."""

    artifact: ExperimentalMaintenanceArtifact
    created: bool


def build_default_experimental_maintenance_artifact(
) -> ExperimentalMaintenanceArtifact:
    """Reproduce the fixed dataset, split, and training-only fitted pipeline."""
    snapshots = generate_predictive_maintenance_snapshots(
        row_count=DEFAULT_SNAPSHOT_COUNT,
        seed=DEFAULT_RANDOM_SEED,
    )
    return train_experimental_maintenance_artifact(
        snapshots,
        dataset_random_seed=DEFAULT_RANDOM_SEED,
        split_random_seed=DEFAULT_SPLIT_RANDOM_SEED,
        model_random_seed=DEFAULT_MODEL_RANDOM_SEED,
    )


def train_experimental_maintenance_artifact(
    snapshots: Iterable[PredictiveMaintenanceSnapshot],
    *,
    dataset_random_seed: int,
    split_random_seed: int,
    model_random_seed: int,
) -> ExperimentalMaintenanceArtifact:
    """Fit the unchanged pipeline on only the established training partition."""
    rows = tuple(snapshots)
    data_split = split_predictive_maintenance_snapshots(
        rows,
        random_seed=split_random_seed,
    )
    trained_model = train_logistic_regression_model(
        data_split,
        random_seed=model_random_seed,
    )
    metadata = ExperimentalArtifactMetadata(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        model_family=MODEL_FAMILY,
        feature_names=PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
        decision_threshold=EXPERIMENTAL_DECISION_THRESHOLD,
        dataset_size=len(rows),
        training_row_count=len(data_split.training),
        validation_row_count=len(data_split.validation),
        test_row_count=len(data_split.test),
        dataset_random_seed=dataset_random_seed,
        split_random_seed=split_random_seed,
        model_random_seed=model_random_seed,
        experimental=True,
        useful_value_gate_passed=False,
        mvp_authority=MVP_AUTHORITY_STATEMENT,
    )
    _validate_metadata(metadata)
    _validate_pipeline(trained_model.pipeline, metadata)
    return ExperimentalMaintenanceArtifact(
        pipeline=trained_model.pipeline,
        metadata=metadata,
    )


def save_experimental_maintenance_artifact(
    artifact: ExperimentalMaintenanceArtifact,
    artifact_directory: Path = DEFAULT_ARTIFACT_DIRECTORY,
) -> ExperimentalArtifactPaths:
    """Save the complete fitted pipeline and transparent JSON metadata."""
    _validate_metadata(artifact.metadata)
    _validate_pipeline(artifact.pipeline, artifact.metadata)
    artifact_directory.mkdir(parents=True, exist_ok=True)
    paths = ExperimentalArtifactPaths(
        model_path=artifact_directory / MODEL_ARTIFACT_FILENAME,
        metadata_path=artifact_directory / METADATA_FILENAME,
    )
    joblib.dump(artifact.pipeline, paths.model_path)
    paths.metadata_path.write_text(
        json.dumps(
            artifact.metadata.to_json_object(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return paths


def load_experimental_maintenance_artifact(
    artifact_directory: Path = DEFAULT_ARTIFACT_DIRECTORY,
) -> ExperimentalMaintenanceArtifact:
    """Load and validate one trusted local experimental artifact pair."""
    paths = ExperimentalArtifactPaths(
        model_path=artifact_directory / MODEL_ARTIFACT_FILENAME,
        metadata_path=artifact_directory / METADATA_FILENAME,
    )
    if not paths.model_path.is_file():
        raise FileNotFoundError(f"Model artifact not found: {paths.model_path}")
    if not paths.metadata_path.is_file():
        raise FileNotFoundError(f"Artifact metadata not found: {paths.metadata_path}")

    try:
        metadata_object = json.loads(
            paths.metadata_path.read_text(encoding="utf-8")
        )
    except (JSONDecodeError, OSError) as error:
        raise ExperimentalArtifactCompatibilityError(
            "Artifact metadata is not valid readable JSON"
        ) from error
    metadata = _metadata_from_json_object(metadata_object)

    try:
        pipeline = joblib.load(paths.model_path)
    except Exception as error:
        raise ExperimentalArtifactCompatibilityError(
            "Model artifact could not be loaded"
        ) from error
    _validate_pipeline(pipeline, metadata)
    return ExperimentalMaintenanceArtifact(
        pipeline=pipeline,
        metadata=metadata,
    )


def prepare_experimental_maintenance_artifact(
    artifact_directory: Path = DEFAULT_ARTIFACT_DIRECTORY,
) -> ExperimentalArtifactPreparation:
    """Reuse a valid artifact pair or reconstruct the frozen experiment."""
    paths = ExperimentalArtifactPaths(
        model_path=artifact_directory / MODEL_ARTIFACT_FILENAME,
        metadata_path=artifact_directory / METADATA_FILENAME,
    )
    if not paths.model_path.exists() and not paths.metadata_path.exists():
        artifact = build_default_experimental_maintenance_artifact()
        save_experimental_maintenance_artifact(artifact, artifact_directory)
        return ExperimentalArtifactPreparation(
            artifact=load_experimental_maintenance_artifact(
                artifact_directory
            ),
            created=True,
        )

    return ExperimentalArtifactPreparation(
        artifact=load_experimental_maintenance_artifact(artifact_directory),
        created=False,
    )


def _metadata_from_json_object(value: Any) -> ExperimentalArtifactMetadata:
    if not isinstance(value, Mapping):
        raise ExperimentalArtifactCompatibilityError(
            "Artifact metadata must be a JSON object"
        )
    required_fields = {
        "schema_version",
        "model_family",
        "feature_names",
        "decision_threshold",
        "dataset_size",
        "training_row_count",
        "validation_row_count",
        "test_row_count",
        "dataset_random_seed",
        "split_random_seed",
        "model_random_seed",
        "experimental",
        "useful_value_gate_passed",
        "mvp_authority",
    }
    missing_fields = required_fields - set(value)
    if missing_fields:
        raise ExperimentalArtifactCompatibilityError(
            "Artifact metadata is missing required fields: "
            + ", ".join(sorted(missing_fields))
        )

    feature_names = value["feature_names"]
    if not isinstance(feature_names, list) or not all(
        isinstance(name, str) for name in feature_names
    ):
        raise ExperimentalArtifactCompatibilityError(
            "Artifact feature_names must be a list of strings"
        )
    try:
        metadata = ExperimentalArtifactMetadata(
            schema_version=value["schema_version"],
            model_family=value["model_family"],
            feature_names=tuple(feature_names),
            decision_threshold=float(value["decision_threshold"]),
            dataset_size=value["dataset_size"],
            training_row_count=value["training_row_count"],
            validation_row_count=value["validation_row_count"],
            test_row_count=value["test_row_count"],
            dataset_random_seed=value["dataset_random_seed"],
            split_random_seed=value["split_random_seed"],
            model_random_seed=value["model_random_seed"],
            experimental=value["experimental"],
            useful_value_gate_passed=value["useful_value_gate_passed"],
            mvp_authority=value["mvp_authority"],
        )
    except (TypeError, ValueError) as error:
        raise ExperimentalArtifactCompatibilityError(
            "Artifact metadata contains invalid field values"
        ) from error
    _validate_metadata(metadata)
    return metadata


def _validate_metadata(metadata: ExperimentalArtifactMetadata) -> None:
    if (
        isinstance(metadata.schema_version, bool)
        or not isinstance(metadata.schema_version, int)
        or metadata.schema_version != ARTIFACT_SCHEMA_VERSION
    ):
        raise ExperimentalArtifactCompatibilityError(
            f"Unsupported artifact schema version: {metadata.schema_version}"
        )
    if metadata.model_family != MODEL_FAMILY:
        raise ExperimentalArtifactCompatibilityError("Unexpected model family")
    if metadata.feature_names != PREDICTIVE_MAINTENANCE_FEATURE_NAMES:
        raise ExperimentalArtifactCompatibilityError(
            "Artifact feature ordering is incompatible"
        )
    if (
        not isfinite(metadata.decision_threshold)
        or not 0.0 <= metadata.decision_threshold <= 1.0
    ):
        raise ExperimentalArtifactCompatibilityError(
            "Artifact decision threshold must be between 0 and 1"
        )
    if metadata.decision_threshold != EXPERIMENTAL_DECISION_THRESHOLD:
        raise ExperimentalArtifactCompatibilityError(
            "Artifact decision threshold does not match the frozen experiment"
        )
    count_values = (
        metadata.dataset_size,
        metadata.training_row_count,
        metadata.validation_row_count,
        metadata.test_row_count,
    )
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count <= 0
        for count in count_values
    ):
        raise ExperimentalArtifactCompatibilityError(
            "Artifact dataset and partition counts must be positive integers"
        )
    if sum(count_values[1:]) != metadata.dataset_size:
        raise ExperimentalArtifactCompatibilityError(
            "Artifact partition counts must equal dataset size"
        )
    seed_values = (
        metadata.dataset_random_seed,
        metadata.split_random_seed,
        metadata.model_random_seed,
    )
    if any(
        isinstance(seed, bool) or not isinstance(seed, int)
        for seed in seed_values
    ):
        raise ExperimentalArtifactCompatibilityError(
            "Artifact reproducibility seeds must be integers"
        )
    if metadata.experimental is not True:
        raise ExperimentalArtifactCompatibilityError(
            "Artifact must be marked experimental"
        )
    if metadata.useful_value_gate_passed is not False:
        raise ExperimentalArtifactCompatibilityError(
            "Artifact must record the failed useful-value gate"
        )
    if metadata.mvp_authority != MVP_AUTHORITY_STATEMENT:
        raise ExperimentalArtifactCompatibilityError(
            "Artifact must preserve deterministic MVP authority"
        )


def _validate_pipeline(
    pipeline: Any,
    metadata: ExperimentalArtifactMetadata,
) -> None:
    if not isinstance(pipeline, Pipeline):
        raise ExperimentalArtifactCompatibilityError(
            "Model artifact must contain a fitted sklearn Pipeline"
        )
    scaler = pipeline.named_steps.get("standard_scaler")
    classifier = pipeline.named_steps.get("logistic_regression")
    if not isinstance(scaler, StandardScaler):
        raise ExperimentalArtifactCompatibilityError(
            "Model pipeline must contain StandardScaler"
        )
    if not isinstance(classifier, LogisticRegression):
        raise ExperimentalArtifactCompatibilityError(
            "Model pipeline must contain LogisticRegression"
        )
    if not hasattr(scaler, "n_samples_seen_") or not hasattr(classifier, "coef_"):
        raise ExperimentalArtifactCompatibilityError(
            "Model pipeline components must be fitted"
        )
    if int(scaler.n_samples_seen_) != metadata.training_row_count:
        raise ExperimentalArtifactCompatibilityError(
            "Scaler fit count does not match training row count"
        )
    if not callable(getattr(pipeline, "predict_proba", None)):
        raise ExperimentalArtifactCompatibilityError(
            "Model pipeline must provide predict_proba"
        )
