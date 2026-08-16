"""Tests for deterministic synthetic predictive-maintenance snapshots."""

from dataclasses import FrozenInstanceError, fields

import pytest

from app.predictive_maintenance_data import (
    DEFAULT_RANDOM_SEED,
    DEFAULT_SNAPSHOT_COUNT,
    PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
    PredictiveMaintenanceSnapshot,
    extract_predictive_maintenance_features,
    generate_predictive_maintenance_snapshots,
)


def test_same_seed_produces_identical_snapshots() -> None:
    assert generate_predictive_maintenance_snapshots(50, seed=42) == (
        generate_predictive_maintenance_snapshots(50, seed=42)
    )


def test_different_seeds_produce_different_snapshots() -> None:
    assert generate_predictive_maintenance_snapshots(50, seed=1) != (
        generate_predictive_maintenance_snapshots(50, seed=2)
    )


def test_requested_and_default_row_counts_are_respected() -> None:
    assert len(generate_predictive_maintenance_snapshots(17)) == 17
    assert (
        len(generate_predictive_maintenance_snapshots())
        == DEFAULT_SNAPSHOT_COUNT
    )


def test_generated_values_satisfy_snapshot_invariants() -> None:
    snapshots = generate_predictive_maintenance_snapshots(500, seed=91)

    assert [snapshot.synthetic_vehicle_id for snapshot in snapshots] == list(
        range(1, 501)
    )
    assert all(snapshot.vehicle_age_years > 0 for snapshot in snapshots)
    assert all(snapshot.current_odometer_km >= 0 for snapshot in snapshots)
    assert all(
        0
        <= snapshot.distance_since_last_scheduled_service_km
        <= snapshot.current_odometer_km
        for snapshot in snapshots
    )
    assert all(
        snapshot.months_since_last_scheduled_service >= 0
        for snapshot in snapshots
    )
    assert all(snapshot.service_interval_km > 0 for snapshot in snapshots)
    assert all(snapshot.service_interval_months > 0 for snapshot in snapshots)
    assert all(snapshot.average_monthly_driving_km > 0 for snapshot in snapshots)
    assert all(
        0.0 <= snapshot.usage_severity_score <= 1.0
        for snapshot in snapshots
    )


def test_target_is_binary_and_both_classes_occur() -> None:
    snapshots = generate_predictive_maintenance_snapshots(1_000, seed=73)
    targets = {
        snapshot.maintenance_needed_within_90_days for snapshot in snapshots
    }

    assert targets == {0, 1}


def test_default_class_distribution_is_not_pathologically_one_sided() -> None:
    snapshots = generate_predictive_maintenance_snapshots(
        seed=DEFAULT_RANDOM_SEED
    )
    positive_ratio = sum(
        snapshot.maintenance_needed_within_90_days for snapshot in snapshots
    ) / len(snapshots)

    assert 0.15 < positive_ratio < 0.85


def test_explicit_feature_set_excludes_target_and_identifier() -> None:
    snapshot = generate_predictive_maintenance_snapshots(1, seed=11)[0]
    feature_values = extract_predictive_maintenance_features(snapshot)

    assert PREDICTIVE_MAINTENANCE_FEATURE_NAMES == (
        "vehicle_age_years",
        "current_odometer_km",
        "distance_since_last_scheduled_service_km",
        "months_since_last_scheduled_service",
        "service_interval_km",
        "service_interval_months",
        "average_monthly_driving_km",
        "usage_severity_score",
    )
    assert len(feature_values) == len(PREDICTIVE_MAINTENANCE_FEATURE_NAMES)
    assert "synthetic_vehicle_id" not in PREDICTIVE_MAINTENANCE_FEATURE_NAMES
    assert (
        "maintenance_needed_within_90_days"
        not in PREDICTIVE_MAINTENANCE_FEATURE_NAMES
    )


def test_no_future_or_latent_generator_fields_are_exposed() -> None:
    public_fields = {field.name for field in fields(PredictiveMaintenanceSnapshot)}

    assert public_fields == {
        "synthetic_vehicle_id",
        *PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
        "maintenance_needed_within_90_days",
    }
    assert not any(
        forbidden_term in field_name
        for field_name in public_fields
        for forbidden_term in (
            "future",
            "latent",
            "noise",
            "probability",
            "event_time",
        )
    )


def test_generated_snapshots_are_immutable() -> None:
    snapshot = generate_predictive_maintenance_snapshots(1)[0]

    with pytest.raises(FrozenInstanceError):
        snapshot.current_odometer_km = 0  # type: ignore[misc]


@pytest.mark.parametrize("row_count", [0, -1, 1.5, True])
def test_invalid_row_count_is_rejected(row_count: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        generate_predictive_maintenance_snapshots(row_count)  # type: ignore[arg-type]
