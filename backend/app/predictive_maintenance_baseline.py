"""Evaluate the deterministic maintenance rule as an experiment baseline."""

from collections.abc import Iterable
from dataclasses import dataclass

from app.maintenance import (
    MaintenanceStatus,
    evaluate_maintenance_due_status,
)
from app.predictive_maintenance_data import PredictiveMaintenanceSnapshot

BASELINE_DUE_SOON_THRESHOLD_PERCENT = 80.0


@dataclass(frozen=True)
class BaselineSnapshotPrediction:
    """Deterministic prediction and independent target for one snapshot."""

    synthetic_vehicle_id: int
    status: MaintenanceStatus
    predicted_target: int
    actual_target: int


@dataclass(frozen=True)
class DeterministicStatusCounts:
    """Counts of each status returned by the existing evaluator."""

    not_due: int
    due_soon: int
    overdue: int


@dataclass(frozen=True)
class BaselineConfusionMatrix:
    """Binary confusion matrix with maintenance-needed as positive."""

    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int


@dataclass(frozen=True)
class BaselineMetrics:
    """Classification metrics for deterministic baseline predictions."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    balanced_accuracy: float


@dataclass(frozen=True)
class PredictiveMaintenanceBaselineEvaluation:
    """Complete deterministic-baseline result for a snapshot collection."""

    total_rows: int
    status_counts: DeterministicStatusCounts
    confusion_matrix: BaselineConfusionMatrix
    metrics: BaselineMetrics
    predictions: tuple[BaselineSnapshotPrediction, ...]


def derive_last_service_odometer_km(
    snapshot: PredictiveMaintenanceSnapshot,
) -> float:
    """Derive the odometer recorded at the snapshot's previous service."""
    return (
        snapshot.current_odometer_km
        - snapshot.distance_since_last_scheduled_service_km
    )


def maintenance_status_to_binary(status: MaintenanceStatus) -> int:
    """Map the existing maintenance status to the fixed baseline prediction."""
    if status is MaintenanceStatus.NOT_DUE:
        return 0
    if status in (MaintenanceStatus.DUE_SOON, MaintenanceStatus.OVERDUE):
        return 1
    raise ValueError(f"Unsupported maintenance status: {status}")


def evaluate_snapshot_baseline(
    snapshot: PredictiveMaintenanceSnapshot,
) -> BaselineSnapshotPrediction:
    """Evaluate one synthetic snapshot with the existing domain function."""
    result = evaluate_maintenance_due_status(
        current_odometer_km=snapshot.current_odometer_km,
        last_service_odometer_km=derive_last_service_odometer_km(snapshot),
        months_since_last_service=snapshot.months_since_last_scheduled_service,
        service_interval_km=snapshot.service_interval_km,
        service_interval_months=snapshot.service_interval_months,
        due_soon_threshold_percent=BASELINE_DUE_SOON_THRESHOLD_PERCENT,
    )
    return BaselineSnapshotPrediction(
        synthetic_vehicle_id=snapshot.synthetic_vehicle_id,
        status=result.status,
        predicted_target=maintenance_status_to_binary(result.status),
        actual_target=snapshot.maintenance_needed_within_90_days,
    )


def evaluate_predictive_maintenance_baseline(
    snapshots: Iterable[PredictiveMaintenanceSnapshot],
) -> PredictiveMaintenanceBaselineEvaluation:
    """Evaluate deterministic predictions and summarize their performance."""
    rows = tuple(snapshots)
    if not rows:
        raise ValueError("At least one predictive-maintenance snapshot is required")

    predictions = tuple(evaluate_snapshot_baseline(snapshot) for snapshot in rows)
    status_counts = DeterministicStatusCounts(
        not_due=sum(
            prediction.status is MaintenanceStatus.NOT_DUE
            for prediction in predictions
        ),
        due_soon=sum(
            prediction.status is MaintenanceStatus.DUE_SOON
            for prediction in predictions
        ),
        overdue=sum(
            prediction.status is MaintenanceStatus.OVERDUE
            for prediction in predictions
        ),
    )
    confusion_matrix = BaselineConfusionMatrix(
        true_positives=sum(
            prediction.actual_target == 1 and prediction.predicted_target == 1
            for prediction in predictions
        ),
        true_negatives=sum(
            prediction.actual_target == 0 and prediction.predicted_target == 0
            for prediction in predictions
        ),
        false_positives=sum(
            prediction.actual_target == 0 and prediction.predicted_target == 1
            for prediction in predictions
        ),
        false_negatives=sum(
            prediction.actual_target == 1 and prediction.predicted_target == 0
            for prediction in predictions
        ),
    )
    return PredictiveMaintenanceBaselineEvaluation(
        total_rows=len(rows),
        status_counts=status_counts,
        confusion_matrix=confusion_matrix,
        metrics=calculate_baseline_metrics(confusion_matrix),
        predictions=predictions,
    )


def calculate_baseline_metrics(
    confusion_matrix: BaselineConfusionMatrix,
) -> BaselineMetrics:
    """Calculate metrics, returning 0.0 for any undefined zero denominator."""
    true_positives = confusion_matrix.true_positives
    true_negatives = confusion_matrix.true_negatives
    false_positives = confusion_matrix.false_positives
    false_negatives = confusion_matrix.false_negatives
    total = true_positives + true_negatives + false_positives + false_negatives

    accuracy = _safe_divide(true_positives + true_negatives, total)
    precision = _safe_divide(true_positives, true_positives + false_positives)
    recall = _safe_divide(true_positives, true_positives + false_negatives)
    negative_recall = _safe_divide(
        true_negatives,
        true_negatives + false_positives,
    )
    f1 = _safe_divide(2.0 * precision * recall, precision + recall)
    return BaselineMetrics(
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        balanced_accuracy=(recall + negative_recall) / 2.0,
    )


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
