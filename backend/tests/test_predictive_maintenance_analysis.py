"""Tests for lightweight predictive-maintenance dataset analysis."""

from math import sqrt

import pytest

from app.predictive_maintenance_analysis import (
    FeatureAnalysis,
    PairwiseFeatureCorrelation,
    PredictiveMaintenanceDatasetAnalysis,
    analyze_predictive_maintenance_snapshots,
)
from app.predictive_maintenance_data import (
    PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
    PredictiveMaintenanceSnapshot,
)


def snapshot(
    synthetic_vehicle_id: int,
    *,
    target: int,
    vehicle_age_years: float = 5.0,
    current_odometer_km: float = 50_000.0,
    distance_since_service_km: float = 5_000.0,
    months_since_service: float = 6.0,
    service_interval_km: float = 10_000.0,
    service_interval_months: float = 12.0,
    average_monthly_driving_km: float = 1_000.0,
    usage_severity_score: float = 0.5,
) -> PredictiveMaintenanceSnapshot:
    return PredictiveMaintenanceSnapshot(
        synthetic_vehicle_id=synthetic_vehicle_id,
        vehicle_age_years=vehicle_age_years,
        current_odometer_km=current_odometer_km,
        distance_since_last_scheduled_service_km=distance_since_service_km,
        months_since_last_scheduled_service=months_since_service,
        service_interval_km=service_interval_km,
        service_interval_months=service_interval_months,
        average_monthly_driving_km=average_monthly_driving_km,
        usage_severity_score=usage_severity_score,
        maintenance_needed_within_90_days=target,
    )


def feature_analysis(
    analysis: PredictiveMaintenanceDatasetAnalysis,
    name: str,
) -> FeatureAnalysis:
    return next(
        feature
        for feature in analysis.feature_analyses
        if feature.name == name
    )


def correlation(
    analysis: PredictiveMaintenanceDatasetAnalysis,
    first_feature: str,
    second_feature: str,
) -> PairwiseFeatureCorrelation:
    return next(
        result
        for result in analysis.feature_correlations
        if {result.first_feature, result.second_feature}
        == {first_feature, second_feature}
    )


def test_dataset_counts_and_positive_rate_are_correct() -> None:
    analysis = analyze_predictive_maintenance_snapshots(
        (
            snapshot(1, target=0),
            snapshot(2, target=1),
            snapshot(3, target=1),
            snapshot(4, target=0),
        )
    )

    assert analysis.total_rows == 4
    assert analysis.positive_count == 2
    assert analysis.negative_count == 2
    assert analysis.positive_rate == 0.5


def test_feature_summaries_use_exactly_the_public_feature_contract() -> None:
    analysis = analyze_predictive_maintenance_snapshots((snapshot(1, target=0),))

    assert tuple(feature.name for feature in analysis.feature_analyses) == (
        PREDICTIVE_MAINTENANCE_FEATURE_NAMES
    )
    assert len(analysis.feature_correlations) == 28


def test_descriptive_statistics_are_correct_for_known_values() -> None:
    analysis = analyze_predictive_maintenance_snapshots(
        tuple(
            snapshot(
                index,
                target=int(index > 2),
                vehicle_age_years=float(index),
            )
            for index in range(1, 5)
        )
    )
    summary = feature_analysis(analysis, "vehicle_age_years").summary

    assert summary.minimum == 1.0
    assert summary.maximum == 4.0
    assert summary.mean == 2.5
    assert summary.standard_deviation == pytest.approx(sqrt(1.25))
    assert summary.median == 2.5


def test_per_class_feature_means_are_correct() -> None:
    analysis = analyze_predictive_maintenance_snapshots(
        tuple(
            snapshot(
                index,
                target=int(index > 2),
                vehicle_age_years=float(index),
            )
            for index in range(1, 5)
        )
    )
    age_analysis = feature_analysis(analysis, "vehicle_age_years")

    assert age_analysis.negative_class_mean == 1.5
    assert age_analysis.positive_class_mean == 3.5


def test_known_perfect_correlations_are_calculated_correctly() -> None:
    analysis = analyze_predictive_maintenance_snapshots(
        tuple(
            snapshot(
                index,
                target=int(index > 2),
                vehicle_age_years=float(index),
                current_odometer_km=float(index * 10_000),
            )
            for index in range(1, 5)
        )
    )

    assert correlation(
        analysis,
        "vehicle_age_years",
        "current_odometer_km",
    ).correlation == pytest.approx(1.0)
    assert feature_analysis(
        analysis,
        "vehicle_age_years",
    ).target_correlation == pytest.approx(0.89442719)


def test_zero_variance_correlation_is_safe_and_reported() -> None:
    analysis = analyze_predictive_maintenance_snapshots(
        (snapshot(1, target=0), snapshot(2, target=1))
    )

    assert feature_analysis(
        analysis,
        "vehicle_age_years",
    ).target_correlation is None
    assert "near_zero_variance_feature" in {
        finding.code for finding in analysis.findings
    }


def test_pathological_class_imbalance_is_reported() -> None:
    rows = tuple(snapshot(index, target=int(index == 20)) for index in range(1, 21))

    analysis = analyze_predictive_maintenance_snapshots(rows)

    assert "pathological_class_imbalance" in {
        finding.code for finding in analysis.findings
    }


def test_extreme_feature_feature_correlation_is_reported() -> None:
    rows = tuple(
        snapshot(
            index,
            target=index % 2,
            vehicle_age_years=float(index),
            current_odometer_km=float(index * 10_000),
        )
        for index in range(1, 11)
    )

    analysis = analyze_predictive_maintenance_snapshots(rows)

    assert "extreme_feature_feature_correlation" in {
        finding.code for finding in analysis.findings
    }


def test_extreme_feature_target_correlation_is_reported() -> None:
    rows = tuple(
        snapshot(
            index,
            target=int(index > 5),
            vehicle_age_years=1.0 if index <= 5 else 2.0,
        )
        for index in range(1, 11)
    )

    analysis = analyze_predictive_maintenance_snapshots(rows)

    assert "extreme_feature_target_correlation" in {
        finding.code for finding in analysis.findings
    }


def test_identifier_target_and_private_fields_cannot_enter_feature_analysis() -> None:
    analysis = analyze_predictive_maintenance_snapshots(
        (snapshot(999, target=1), snapshot(1_000, target=0))
    )
    analyzed_names = {feature.name for feature in analysis.feature_analyses}

    assert analyzed_names == set(PREDICTIVE_MAINTENANCE_FEATURE_NAMES)
    assert "synthetic_vehicle_id" not in analyzed_names
    assert "maintenance_needed_within_90_days" not in analyzed_names
    assert not any(
        forbidden_term in feature_name
        for feature_name in analyzed_names
        for forbidden_term in ("future", "latent", "noise", "probability")
    )


def test_empty_dataset_is_rejected() -> None:
    with pytest.raises(ValueError, match="At least one"):
        analyze_predictive_maintenance_snapshots(())
