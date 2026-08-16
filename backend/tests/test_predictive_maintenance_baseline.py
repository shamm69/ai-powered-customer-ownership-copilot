"""Tests for the deterministic predictive-maintenance baseline."""

from dataclasses import FrozenInstanceError
from unittest.mock import patch

import pytest

from app.maintenance import MaintenanceDueResult, MaintenanceStatus
from app.predictive_maintenance_baseline import (
    BASELINE_DUE_SOON_THRESHOLD_PERCENT,
    BaselineConfusionMatrix,
    BaselineMetrics,
    calculate_baseline_metrics,
    derive_last_service_odometer_km,
    evaluate_predictive_maintenance_baseline,
    evaluate_snapshot_baseline,
    maintenance_status_to_binary,
)
from app.predictive_maintenance_data import PredictiveMaintenanceSnapshot


def snapshot(
    synthetic_vehicle_id: int,
    *,
    target: int,
    distance_since_service_km: float = 4_000.0,
    months_since_service: float = 4.0,
) -> PredictiveMaintenanceSnapshot:
    return PredictiveMaintenanceSnapshot(
        synthetic_vehicle_id=synthetic_vehicle_id,
        vehicle_age_years=5.0,
        current_odometer_km=20_000.0,
        distance_since_last_scheduled_service_km=distance_since_service_km,
        months_since_last_scheduled_service=months_since_service,
        service_interval_km=10_000.0,
        service_interval_months=12.0,
        average_monthly_driving_km=1_000.0,
        usage_severity_score=0.5,
        maintenance_needed_within_90_days=target,
    )


def test_last_service_odometer_is_derived_from_snapshot_distance() -> None:
    row = snapshot(1, target=0, distance_since_service_km=4_500.0)

    assert derive_last_service_odometer_km(row) == 15_500.0


def test_snapshot_evaluation_reuses_existing_domain_evaluator() -> None:
    row = snapshot(1, target=0, distance_since_service_km=4_500.0)
    domain_result = MaintenanceDueResult(
        status=MaintenanceStatus.NOT_DUE,
        kilometres_travelled_since_last_service=4_500.0,
        kilometres_remaining=5_500.0,
        months_remaining=8.0,
        reasons=("Domain result",),
    )

    with patch(
        "app.predictive_maintenance_baseline.evaluate_maintenance_due_status",
        return_value=domain_result,
    ) as evaluator:
        prediction = evaluate_snapshot_baseline(row)

    evaluator.assert_called_once_with(
        current_odometer_km=20_000.0,
        last_service_odometer_km=15_500.0,
        months_since_last_service=4.0,
        service_interval_km=10_000.0,
        service_interval_months=12.0,
        due_soon_threshold_percent=BASELINE_DUE_SOON_THRESHOLD_PERCENT,
    )
    assert prediction.status is MaintenanceStatus.NOT_DUE


@pytest.mark.parametrize(
    ("status", "expected_prediction"),
    [
        (MaintenanceStatus.NOT_DUE, 0),
        (MaintenanceStatus.DUE_SOON, 1),
        (MaintenanceStatus.OVERDUE, 1),
    ],
)
def test_exact_status_to_binary_mapping(
    status: MaintenanceStatus,
    expected_prediction: int,
) -> None:
    assert maintenance_status_to_binary(status) == expected_prediction


def test_known_not_due_snapshot_maps_to_zero() -> None:
    prediction = evaluate_snapshot_baseline(snapshot(1, target=0))

    assert prediction.status is MaintenanceStatus.NOT_DUE
    assert prediction.predicted_target == 0


def test_known_due_soon_snapshot_maps_to_one() -> None:
    prediction = evaluate_snapshot_baseline(
        snapshot(1, target=1, distance_since_service_km=8_000.0)
    )

    assert prediction.status is MaintenanceStatus.DUE_SOON
    assert prediction.predicted_target == 1


def test_known_overdue_snapshot_maps_to_one() -> None:
    prediction = evaluate_snapshot_baseline(
        snapshot(1, target=1, distance_since_service_km=10_000.0)
    )

    assert prediction.status is MaintenanceStatus.OVERDUE
    assert prediction.predicted_target == 1


def test_confusion_matrix_status_counts_and_metrics_are_correct() -> None:
    rows = (
        snapshot(1, target=1, distance_since_service_km=8_000.0),
        snapshot(2, target=0),
        snapshot(3, target=0, distance_since_service_km=10_000.0),
        snapshot(4, target=1),
    )

    evaluation = evaluate_predictive_maintenance_baseline(rows)

    assert evaluation.confusion_matrix == BaselineConfusionMatrix(
        true_positives=1,
        true_negatives=1,
        false_positives=1,
        false_negatives=1,
    )
    assert evaluation.status_counts.not_due == 2
    assert evaluation.status_counts.due_soon == 1
    assert evaluation.status_counts.overdue == 1
    assert evaluation.metrics == BaselineMetrics(
        accuracy=0.5,
        precision=0.5,
        recall=0.5,
        f1=0.5,
        balanced_accuracy=0.5,
    )


def test_metric_calculations_are_correct_for_known_counts() -> None:
    metrics = calculate_baseline_metrics(
        BaselineConfusionMatrix(
            true_positives=6,
            true_negatives=8,
            false_positives=2,
            false_negatives=4,
        )
    )

    assert metrics.accuracy == 0.7
    assert metrics.precision == 0.75
    assert metrics.recall == 0.6
    assert metrics.f1 == pytest.approx(2 * 0.75 * 0.6 / (0.75 + 0.6))
    assert metrics.balanced_accuracy == 0.7


def test_zero_denominators_return_explicit_zero_values() -> None:
    metrics = calculate_baseline_metrics(
        BaselineConfusionMatrix(
            true_positives=0,
            true_negatives=5,
            false_positives=0,
            false_negatives=0,
        )
    )

    assert metrics.accuracy == 1.0
    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0
    assert metrics.balanced_accuracy == 0.5


def test_input_snapshots_are_not_mutated() -> None:
    rows = (snapshot(1, target=0), snapshot(2, target=1))
    original_rows = tuple(rows)

    evaluate_predictive_maintenance_baseline(rows)

    assert rows == original_rows


def test_result_structures_are_immutable() -> None:
    evaluation = evaluate_predictive_maintenance_baseline(
        (snapshot(1, target=0),)
    )

    with pytest.raises(FrozenInstanceError):
        evaluation.total_rows = 0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        evaluation.metrics.accuracy = 0.0  # type: ignore[misc]


def test_empty_snapshot_collection_is_rejected() -> None:
    with pytest.raises(ValueError, match="At least one"):
        evaluate_predictive_maintenance_baseline(())
