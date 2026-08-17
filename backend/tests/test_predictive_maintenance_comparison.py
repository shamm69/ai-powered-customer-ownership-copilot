"""Tests for side-by-side deterministic and experimental signals."""

from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from unittest.mock import patch

import pytest

from app.maintenance import MaintenanceDueResult, MaintenanceStatus
from app.predictive_maintenance_artifact import (
    DEFAULT_ARTIFACT_DIRECTORY,
    METADATA_FILENAME,
    MODEL_ARTIFACT_FILENAME,
)
from app.predictive_maintenance_baseline import (
    BASELINE_DUE_SOON_THRESHOLD_PERCENT,
)
from app.predictive_maintenance_comparison import (
    MaintenancePredictionComparison,
    MaintenancePredictionComparisonService,
    MaintenanceSignalRelationship,
    classify_signal_relationship,
    load_default_maintenance_prediction_comparison_service,
)
from app.predictive_maintenance_data import PREDICTIVE_MAINTENANCE_FEATURE_NAMES
from app.predictive_maintenance_prediction import (
    ExperimentalMaintenancePrediction,
    PredictiveMaintenanceFeatureInput,
)


class FakeExperimentalPredictor:
    def __init__(self, result: ExperimentalMaintenancePrediction) -> None:
        self.result = result
        self.received_input: PredictiveMaintenanceFeatureInput | None = None
        self.call_count = 0

    def predict(
        self,
        feature_input: PredictiveMaintenanceFeatureInput,
    ) -> ExperimentalMaintenancePrediction:
        self.call_count += 1
        self.received_input = feature_input
        return self.result


def feature_input(
    *,
    distance_since_service_km: float = 7_500.0,
) -> PredictiveMaintenanceFeatureInput:
    return PredictiveMaintenanceFeatureInput(
        vehicle_age_years=6.0,
        current_odometer_km=72_000.0,
        distance_since_last_scheduled_service_km=distance_since_service_km,
        months_since_last_scheduled_service=8.0,
        service_interval_km=10_000.0,
        service_interval_months=12.0,
        average_monthly_driving_km=1_100.0,
        usage_severity_score=0.65,
    )


def experimental_result(prediction: int) -> ExperimentalMaintenancePrediction:
    return ExperimentalMaintenancePrediction(
        maintenance_needed_within_90_days_prediction=prediction,
        positive_class_probability=0.64 if prediction else 0.12,
        threshold=0.19,
        experimental=True,
        artifact_schema_version=1,
    )


def domain_result(status: MaintenanceStatus) -> MaintenanceDueResult:
    return MaintenanceDueResult(
        status=status,
        kilometres_travelled_since_last_service=7_500.0,
        kilometres_remaining=2_500.0,
        months_remaining=4.0,
        reasons=("Original deterministic reason",),
    )


def test_existing_evaluator_and_fixed_threshold_are_reused() -> None:
    inputs = feature_input()
    expected_domain_result = domain_result(MaintenanceStatus.NOT_DUE)
    predictor = FakeExperimentalPredictor(experimental_result(0))
    service = MaintenancePredictionComparisonService(predictor)

    with patch(
        "app.predictive_maintenance_comparison.evaluate_maintenance_due_status",
        return_value=expected_domain_result,
    ) as evaluator:
        service.compare(inputs)

    evaluator.assert_called_once_with(
        current_odometer_km=72_000.0,
        last_service_odometer_km=64_500.0,
        months_since_last_service=8.0,
        service_interval_km=10_000.0,
        service_interval_months=12.0,
        due_soon_threshold_percent=BASELINE_DUE_SOON_THRESHOLD_PERCENT,
    )


def test_existing_prediction_service_is_injected_and_reused() -> None:
    inputs = feature_input()
    expected_ml_result = experimental_result(0)
    predictor = FakeExperimentalPredictor(expected_ml_result)

    comparison = MaintenancePredictionComparisonService(predictor).compare(inputs)

    assert predictor.call_count == 1
    assert predictor.received_input is inputs
    assert comparison.experimental_result is expected_ml_result


def test_original_deterministic_result_is_preserved() -> None:
    expected_domain_result = domain_result(MaintenanceStatus.DUE_SOON)
    service = MaintenancePredictionComparisonService(
        FakeExperimentalPredictor(experimental_result(0))
    )

    with patch(
        "app.predictive_maintenance_comparison.evaluate_maintenance_due_status",
        return_value=expected_domain_result,
    ):
        comparison = service.compare(feature_input())

    assert comparison.deterministic_result is expected_domain_result
    assert comparison.deterministic_result.reasons == (
        "Original deterministic reason",
    )


@pytest.mark.parametrize(
    ("status", "expected_signal"),
    [
        (MaintenanceStatus.NOT_DUE, 0),
        (MaintenanceStatus.DUE_SOON, 1),
        (MaintenanceStatus.OVERDUE, 1),
    ],
)
def test_deterministic_status_uses_established_binary_mapping(
    status: MaintenanceStatus,
    expected_signal: int,
) -> None:
    service = MaintenancePredictionComparisonService(
        FakeExperimentalPredictor(experimental_result(0))
    )

    with patch(
        "app.predictive_maintenance_comparison.evaluate_maintenance_due_status",
        return_value=domain_result(status),
    ):
        comparison = service.compare(feature_input())

    assert comparison.deterministic_binary_signal == expected_signal


@pytest.mark.parametrize(
    ("deterministic_signal", "ml_signal", "expected_relationship"),
    [
        (0, 0, MaintenanceSignalRelationship.AGREE_NEGATIVE),
        (1, 1, MaintenanceSignalRelationship.AGREE_POSITIVE),
        (1, 0, MaintenanceSignalRelationship.DETERMINISTIC_ONLY_POSITIVE),
        (0, 1, MaintenanceSignalRelationship.ML_ONLY_POSITIVE),
    ],
)
def test_all_four_signal_relationships(
    deterministic_signal: int,
    ml_signal: int,
    expected_relationship: MaintenanceSignalRelationship,
) -> None:
    assert (
        classify_signal_relationship(deterministic_signal, ml_signal)
        is expected_relationship
    )


@pytest.mark.parametrize("signals", [(-1, 0), (0, 2), (1, -1)])
def test_non_binary_comparison_signals_are_rejected(
    signals: tuple[int, int],
) -> None:
    with pytest.raises(ValueError, match="must be binary"):
        classify_signal_relationship(*signals)


def test_ml_signal_never_changes_deterministic_status() -> None:
    expected_domain_result = domain_result(MaintenanceStatus.NOT_DUE)
    service = MaintenancePredictionComparisonService(
        FakeExperimentalPredictor(experimental_result(1))
    )

    with patch(
        "app.predictive_maintenance_comparison.evaluate_maintenance_due_status",
        return_value=expected_domain_result,
    ):
        comparison = service.compare(feature_input())

    assert comparison.deterministic_result.status is MaintenanceStatus.NOT_DUE
    assert comparison.experimental_ml_binary_signal == 1
    assert (
        comparison.relationship
        is MaintenanceSignalRelationship.ML_ONLY_POSITIVE
    )


def test_comparison_has_no_combined_or_final_status() -> None:
    comparison_fields = {
        field.name for field in fields(MaintenancePredictionComparison)
    }

    assert comparison_fields == {
        "deterministic_result",
        "experimental_result",
        "deterministic_binary_signal",
        "experimental_ml_binary_signal",
        "relationship",
    }
    assert "final_status" not in comparison_fields
    assert "combined_prediction" not in comparison_fields


def test_comparison_result_is_immutable() -> None:
    comparison = MaintenancePredictionComparisonService(
        FakeExperimentalPredictor(experimental_result(0))
    ).compare(feature_input())

    with pytest.raises(FrozenInstanceError):
        comparison.relationship = (  # type: ignore[misc]
            MaintenanceSignalRelationship.AGREE_POSITIVE
        )


def test_input_is_not_mutated() -> None:
    inputs = feature_input()
    original = replace(inputs)

    MaintenancePredictionComparisonService(
        FakeExperimentalPredictor(experimental_result(0))
    ).compare(inputs)

    assert inputs == original


def test_runtime_input_requires_only_eight_public_features() -> None:
    assert tuple(
        field.name for field in fields(PredictiveMaintenanceFeatureInput)
    ) == PREDICTIVE_MAINTENANCE_FEATURE_NAMES


def test_fake_comparison_does_not_load_or_train_an_artifact() -> None:
    with (
        patch(
            "app.predictive_maintenance_artifact.load_experimental_maintenance_artifact",
            side_effect=AssertionError("Comparison must not load an artifact"),
        ),
        patch(
            "app.predictive_maintenance_model.train_logistic_regression_model",
            side_effect=AssertionError("Comparison must not train a model"),
        ),
    ):
        comparison = MaintenancePredictionComparisonService(
            FakeExperimentalPredictor(experimental_result(0))
        ).compare(feature_input())

    assert comparison.experimental_ml_binary_signal == 0


def test_default_composition_uses_existing_artifact_without_training() -> None:
    model_path = DEFAULT_ARTIFACT_DIRECTORY / MODEL_ARTIFACT_FILENAME
    metadata_path = DEFAULT_ARTIFACT_DIRECTORY / METADATA_FILENAME
    if not model_path.is_file() or not metadata_path.is_file():
        pytest.skip("Local ignored experimental artifact is not present")

    with patch(
        "app.predictive_maintenance_model.train_logistic_regression_model",
        side_effect=AssertionError("Default composition must not train"),
    ):
        service = load_default_maintenance_prediction_comparison_service()
        comparison = service.compare(feature_input())

    assert comparison.experimental_result.experimental is True
    assert comparison.experimental_result.threshold == 0.19


def test_missing_default_artifact_failure_is_clear(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Model artifact not found"):
        load_default_maintenance_prediction_comparison_service(tmp_path)
