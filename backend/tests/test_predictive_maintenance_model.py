"""Tests for predictive-maintenance splitting and model training."""

from dataclasses import FrozenInstanceError

import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from app.predictive_maintenance_data import (
    PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
    PredictiveMaintenanceSnapshot,
    extract_predictive_maintenance_features,
    generate_predictive_maintenance_snapshots,
)
from app.predictive_maintenance_model import (
    PredictiveMaintenanceDataSplit,
    TrainedPredictiveMaintenanceModel,
    build_logistic_regression_pipeline,
    build_predictive_maintenance_feature_matrix,
    evaluate_model_validation_metrics,
    extract_predictive_maintenance_targets,
    split_predictive_maintenance_snapshots,
    train_logistic_regression_model,
)


@pytest.fixture(scope="module")
def snapshots() -> tuple[PredictiveMaintenanceSnapshot, ...]:
    return generate_predictive_maintenance_snapshots(1_500, seed=137)


@pytest.fixture(scope="module")
def data_split(
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
) -> PredictiveMaintenanceDataSplit:
    return split_predictive_maintenance_snapshots(snapshots, random_seed=19)


@pytest.fixture(scope="module")
def trained_model(
    data_split: PredictiveMaintenanceDataSplit,
) -> TrainedPredictiveMaintenanceModel:
    return train_logistic_regression_model(data_split, random_seed=23)


def membership(
    data_split: PredictiveMaintenanceDataSplit,
) -> tuple[frozenset[int], ...]:
    return tuple(
        frozenset(snapshot.synthetic_vehicle_id for snapshot in partition)
        for partition in (
            data_split.training,
            data_split.validation,
            data_split.test,
        )
    )


def positive_rate(rows: tuple[PredictiveMaintenanceSnapshot, ...]) -> float:
    return sum(row.maintenance_needed_within_90_days for row in rows) / len(rows)


def test_same_seed_produces_identical_split_membership(
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
) -> None:
    first = split_predictive_maintenance_snapshots(snapshots, random_seed=7)
    second = split_predictive_maintenance_snapshots(snapshots, random_seed=7)

    assert membership(first) == membership(second)


def test_different_seeds_change_split_membership(
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
) -> None:
    first = split_predictive_maintenance_snapshots(snapshots, random_seed=7)
    second = split_predictive_maintenance_snapshots(snapshots, random_seed=8)

    assert membership(first) != membership(second)


def test_partitions_are_disjoint_and_cover_every_snapshot_once(
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
    data_split: PredictiveMaintenanceDataSplit,
) -> None:
    training_ids = {row.synthetic_vehicle_id for row in data_split.training}
    validation_ids = {row.synthetic_vehicle_id for row in data_split.validation}
    test_ids = {row.synthetic_vehicle_id for row in data_split.test}

    assert training_ids.isdisjoint(validation_ids)
    assert training_ids.isdisjoint(test_ids)
    assert validation_ids.isdisjoint(test_ids)
    assert training_ids | validation_ids | test_ids == {
        row.synthetic_vehicle_id for row in snapshots
    }
    assert sum(len(partition) for partition in membership(data_split)) == len(
        snapshots
    )


def test_split_sizes_are_approximately_70_15_15(
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
    data_split: PredictiveMaintenanceDataSplit,
) -> None:
    total = len(snapshots)

    assert len(data_split.training) / total == pytest.approx(0.70, abs=0.01)
    assert len(data_split.validation) / total == pytest.approx(0.15, abs=0.01)
    assert len(data_split.test) / total == pytest.approx(0.15, abs=0.01)


def test_stratification_preserves_both_classes_and_approximate_rates(
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
    data_split: PredictiveMaintenanceDataSplit,
) -> None:
    overall_rate = positive_rate(snapshots)

    for partition in (
        data_split.training,
        data_split.validation,
        data_split.test,
    ):
        assert set(extract_predictive_maintenance_targets(partition)) == {0, 1}
        assert positive_rate(partition) == pytest.approx(overall_rate, abs=0.01)


def test_feature_matrix_uses_exactly_the_established_eight_features() -> None:
    rows = generate_predictive_maintenance_snapshots(2, seed=44)

    feature_matrix = build_predictive_maintenance_feature_matrix(rows)

    assert len(PREDICTIVE_MAINTENANCE_FEATURE_NAMES) == 8
    assert feature_matrix == tuple(
        extract_predictive_maintenance_features(row) for row in rows
    )
    assert all(len(feature_row) == 8 for feature_row in feature_matrix)


def test_target_and_identifier_are_excluded_from_model_features() -> None:
    original = generate_predictive_maintenance_snapshots(1, seed=81)[0]
    changed_identity_and_target = PredictiveMaintenanceSnapshot(
        synthetic_vehicle_id=999,
        vehicle_age_years=original.vehicle_age_years,
        current_odometer_km=original.current_odometer_km,
        distance_since_last_scheduled_service_km=(
            original.distance_since_last_scheduled_service_km
        ),
        months_since_last_scheduled_service=(
            original.months_since_last_scheduled_service
        ),
        service_interval_km=original.service_interval_km,
        service_interval_months=original.service_interval_months,
        average_monthly_driving_km=original.average_monthly_driving_km,
        usage_severity_score=original.usage_severity_score,
        maintenance_needed_within_90_days=(
            1 - original.maintenance_needed_within_90_days
        ),
    )

    assert build_predictive_maintenance_feature_matrix((original,)) == (
        build_predictive_maintenance_feature_matrix((changed_identity_and_target,))
    )


def test_pipeline_contains_scaler_and_logistic_regression() -> None:
    pipeline = build_logistic_regression_pipeline()

    assert isinstance(pipeline.named_steps["standard_scaler"], StandardScaler)
    assert isinstance(
        pipeline.named_steps["logistic_regression"],
        LogisticRegression,
    )


def test_model_fits_training_data_and_preprocessing_sees_only_training_rows(
    trained_model: TrainedPredictiveMaintenanceModel,
) -> None:
    scaler = trained_model.pipeline.named_steps["standard_scaler"]

    assert isinstance(scaler, StandardScaler)
    assert scaler.n_samples_seen_ == len(trained_model.data_split.training)
    assert hasattr(
        trained_model.pipeline.named_steps["logistic_regression"],
        "coef_",
    )


def test_predict_returns_ordered_binary_predictions(
    trained_model: TrainedPredictiveMaintenanceModel,
) -> None:
    rows = trained_model.data_split.validation[:20]
    features = build_predictive_maintenance_feature_matrix(rows)

    predictions = trained_model.pipeline.predict(features)
    individual_predictions = tuple(
        int(
            trained_model.pipeline.predict(
                build_predictive_maintenance_feature_matrix((row,))
            )[0]
        )
        for row in rows
    )

    assert len(predictions) == len(rows)
    assert set(predictions).issubset({0, 1})
    assert tuple(int(prediction) for prediction in predictions) == (
        individual_predictions
    )


def test_predict_proba_returns_ordered_valid_probabilities(
    trained_model: TrainedPredictiveMaintenanceModel,
) -> None:
    rows = trained_model.data_split.validation[:20]
    probabilities = trained_model.pipeline.predict_proba(
        build_predictive_maintenance_feature_matrix(rows)
    )

    assert probabilities.shape == (len(rows), 2)
    assert all(0.0 <= value <= 1.0 for row in probabilities for value in row)
    assert all(sum(row) == pytest.approx(1.0) for row in probabilities)


def test_validation_metrics_are_finite_probabilities(
    trained_model: TrainedPredictiveMaintenanceModel,
) -> None:
    metrics = evaluate_model_validation_metrics(
        trained_model,
        trained_model.data_split.validation,
    )

    assert all(
        0.0 <= value <= 1.0
        for value in (
            metrics.accuracy,
            metrics.precision,
            metrics.recall,
            metrics.f1,
            metrics.balanced_accuracy,
            metrics.roc_auc,
            metrics.average_precision,
        )
    )


def test_input_snapshots_are_not_mutated(
    snapshots: tuple[PredictiveMaintenanceSnapshot, ...],
) -> None:
    original_snapshots = tuple(snapshots)

    data_split = split_predictive_maintenance_snapshots(snapshots)
    train_logistic_regression_model(data_split)

    assert snapshots == original_snapshots


def test_split_and_training_wrappers_are_immutable(
    data_split: PredictiveMaintenanceDataSplit,
    trained_model: TrainedPredictiveMaintenanceModel,
) -> None:
    with pytest.raises(FrozenInstanceError):
        data_split.training = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        trained_model.feature_names = ()  # type: ignore[misc]


def test_empty_snapshots_are_rejected() -> None:
    with pytest.raises(ValueError, match="At least one"):
        split_predictive_maintenance_snapshots(())
