"""Reproducible splitting and Logistic Regression training for the experiment."""

from collections.abc import Iterable
from dataclasses import dataclass

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.predictive_maintenance_data import (
    PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
    PredictiveMaintenanceSnapshot,
    extract_predictive_maintenance_features,
)

DEFAULT_SPLIT_RANDOM_SEED = 42
DEFAULT_MODEL_RANDOM_SEED = 42
DEFAULT_CLASSIFICATION_THRESHOLD = 0.5


@dataclass(frozen=True)
class PredictiveMaintenanceDataSplit:
    """Disjoint stratified snapshot partitions for model development."""

    training: tuple[PredictiveMaintenanceSnapshot, ...]
    validation: tuple[PredictiveMaintenanceSnapshot, ...]
    test: tuple[PredictiveMaintenanceSnapshot, ...]


@dataclass(frozen=True)
class TrainedPredictiveMaintenanceModel:
    """A fitted pipeline paired with the split used to train it."""

    pipeline: Pipeline
    data_split: PredictiveMaintenanceDataSplit
    feature_names: tuple[str, ...] = PREDICTIVE_MAINTENANCE_FEATURE_NAMES


@dataclass(frozen=True)
class ModelValidationMetrics:
    """Validation-only sanity metrics for a fitted binary classifier."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    balanced_accuracy: float
    roc_auc: float
    average_precision: float


def split_predictive_maintenance_snapshots(
    snapshots: Iterable[PredictiveMaintenanceSnapshot],
    random_seed: int = DEFAULT_SPLIT_RANDOM_SEED,
) -> PredictiveMaintenanceDataSplit:
    """Create deterministic stratified 70/15/15 snapshot partitions."""
    rows = tuple(snapshots)
    if not rows:
        raise ValueError("At least one predictive-maintenance snapshot is required")

    targets = extract_predictive_maintenance_targets(rows)
    training_rows, temporary_rows = train_test_split(
        rows,
        test_size=0.30,
        random_state=random_seed,
        stratify=targets,
    )
    temporary_targets = extract_predictive_maintenance_targets(temporary_rows)
    validation_rows, test_rows = train_test_split(
        temporary_rows,
        test_size=0.50,
        random_state=random_seed,
        stratify=temporary_targets,
    )
    return PredictiveMaintenanceDataSplit(
        training=tuple(training_rows),
        validation=tuple(validation_rows),
        test=tuple(test_rows),
    )


def build_predictive_maintenance_feature_matrix(
    snapshots: Iterable[PredictiveMaintenanceSnapshot],
) -> tuple[tuple[float, ...], ...]:
    """Extract only the established ordered eight-feature model contract."""
    return tuple(
        extract_predictive_maintenance_features(snapshot)
        for snapshot in snapshots
    )


def extract_predictive_maintenance_targets(
    snapshots: Iterable[PredictiveMaintenanceSnapshot],
) -> tuple[int, ...]:
    """Extract binary future-outcome targets separately from model features."""
    return tuple(
        snapshot.maintenance_needed_within_90_days for snapshot in snapshots
    )


def build_logistic_regression_pipeline(
    random_seed: int = DEFAULT_MODEL_RANDOM_SEED,
) -> Pipeline:
    """Build the fixed, CPU-friendly preprocessing and classifier pipeline."""
    return Pipeline(
        steps=(
            ("standard_scaler", StandardScaler()),
            (
                "logistic_regression",
                LogisticRegression(
                    random_state=random_seed,
                    max_iter=1_000,
                ),
            ),
        )
    )


def train_logistic_regression_model(
    data_split: PredictiveMaintenanceDataSplit,
    random_seed: int = DEFAULT_MODEL_RANDOM_SEED,
) -> TrainedPredictiveMaintenanceModel:
    """Fit preprocessing and Logistic Regression using training rows only."""
    pipeline = build_logistic_regression_pipeline(random_seed)
    pipeline.fit(
        build_predictive_maintenance_feature_matrix(data_split.training),
        extract_predictive_maintenance_targets(data_split.training),
    )
    return TrainedPredictiveMaintenanceModel(
        pipeline=pipeline,
        data_split=data_split,
    )


def evaluate_model_validation_metrics(
    trained_model: TrainedPredictiveMaintenanceModel,
    snapshots: Iterable[PredictiveMaintenanceSnapshot],
    classification_threshold: float = DEFAULT_CLASSIFICATION_THRESHOLD,
) -> ModelValidationMetrics:
    """Calculate sanity metrics for supplied non-test snapshots."""
    rows = tuple(snapshots)
    if not rows:
        raise ValueError("At least one validation snapshot is required")
    if not 0.0 <= classification_threshold <= 1.0:
        raise ValueError("classification_threshold must be between 0 and 1")

    features = build_predictive_maintenance_feature_matrix(rows)
    targets = extract_predictive_maintenance_targets(rows)
    positive_probabilities = trained_model.pipeline.predict_proba(features)[:, 1]
    predictions = tuple(
        int(probability >= classification_threshold)
        for probability in positive_probabilities
    )
    return ModelValidationMetrics(
        accuracy=float(accuracy_score(targets, predictions)),
        precision=float(precision_score(targets, predictions, zero_division=0)),
        recall=float(recall_score(targets, predictions, zero_division=0)),
        f1=float(f1_score(targets, predictions, zero_division=0)),
        balanced_accuracy=float(balanced_accuracy_score(targets, predictions)),
        roc_auc=float(roc_auc_score(targets, positive_probabilities)),
        average_precision=float(
            average_precision_score(targets, positive_probabilities)
        ),
    )
