"""Tests for the experimental maintenance prediction service."""

from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from sklearn.pipeline import Pipeline

from app.predictive_maintenance_artifact import (
    ARTIFACT_SCHEMA_VERSION,
    DEFAULT_ARTIFACT_DIRECTORY,
    EXPERIMENTAL_DECISION_THRESHOLD,
    MODEL_ARTIFACT_FILENAME,
    METADATA_FILENAME,
    MODEL_FAMILY,
    MVP_AUTHORITY_STATEMENT,
    ExperimentalArtifactMetadata,
    ExperimentalMaintenanceArtifact,
)
from app.predictive_maintenance_data import PREDICTIVE_MAINTENANCE_FEATURE_NAMES
from app.predictive_maintenance_prediction import (
    ExperimentalMaintenancePredictionError,
    ExperimentalMaintenancePredictionService,
    PredictiveMaintenanceFeatureInput,
    load_default_experimental_prediction_service,
)


class FakeProbabilityPipeline:
    def __init__(
        self,
        probability_output: Any,
        classes: tuple[int, ...] = (0, 1),
    ) -> None:
        self.probability_output = probability_output
        self.classes_ = classes
        self.received_features: Any = None
        self.predict_proba_calls = 0

    def predict_proba(self, features: Any) -> Any:
        self.predict_proba_calls += 1
        self.received_features = features
        return self.probability_output

    def predict(self, _: Any) -> Any:
        raise AssertionError("Pipeline.predict() must not be used")


def metadata(threshold: float = 0.19) -> ExperimentalArtifactMetadata:
    return ExperimentalArtifactMetadata(
        schema_version=ARTIFACT_SCHEMA_VERSION,
        model_family=MODEL_FAMILY,
        feature_names=PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
        decision_threshold=threshold,
        dataset_size=1_500,
        training_row_count=1_050,
        validation_row_count=225,
        test_row_count=225,
        dataset_random_seed=20_260_817,
        split_random_seed=42,
        model_random_seed=42,
        experimental=True,
        useful_value_gate_passed=False,
        mvp_authority=MVP_AUTHORITY_STATEMENT,
    )


def feature_input() -> PredictiveMaintenanceFeatureInput:
    return PredictiveMaintenanceFeatureInput(
        vehicle_age_years=6.0,
        current_odometer_km=72_000.0,
        distance_since_last_scheduled_service_km=7_500.0,
        months_since_last_scheduled_service=8.0,
        service_interval_km=10_000.0,
        service_interval_months=12.0,
        average_monthly_driving_km=1_100.0,
        usage_severity_score=0.65,
    )


def service(
    probability_output: Any,
    *,
    threshold: float = 0.19,
    classes: tuple[int, ...] = (0, 1),
) -> tuple[ExperimentalMaintenancePredictionService, FakeProbabilityPipeline]:
    pipeline = FakeProbabilityPipeline(probability_output, classes)
    artifact = ExperimentalMaintenanceArtifact(
        pipeline=cast(Pipeline, pipeline),
        metadata=metadata(threshold),
    )
    return ExperimentalMaintenancePredictionService(artifact), pipeline


def test_exact_eight_feature_order_is_supplied_to_predict_proba() -> None:
    prediction_service, pipeline = service(((0.7, 0.3),))
    inputs = feature_input()

    prediction_service.predict(inputs)

    assert PREDICTIVE_MAINTENANCE_FEATURE_NAMES == tuple(
        field.name for field in fields(PredictiveMaintenanceFeatureInput)
    )
    assert pipeline.received_features == (inputs.as_feature_values(),)


def test_target_and_identifier_cannot_enter_model_input() -> None:
    input_fields = {field.name for field in fields(PredictiveMaintenanceFeatureInput)}

    assert input_fields == set(PREDICTIVE_MAINTENANCE_FEATURE_NAMES)
    assert "maintenance_needed_within_90_days" not in input_fields
    assert "synthetic_vehicle_id" not in input_fields


def test_predict_proba_positive_class_is_used_without_predict() -> None:
    prediction_service, pipeline = service(((0.64, 0.36),))

    result = prediction_service.predict(feature_input())

    assert pipeline.predict_proba_calls == 1
    assert result.positive_class_probability == 0.36


@pytest.mark.parametrize(
    ("probability", "expected_prediction"),
    [(0.18, 0), (0.19, 1), (0.20, 1)],
)
def test_probability_uses_inclusive_stored_threshold(
    probability: float,
    expected_prediction: int,
) -> None:
    prediction_service, _ = service(((1.0 - probability, probability),))

    result = prediction_service.predict(feature_input())

    assert result.maintenance_needed_within_90_days_prediction == (
        expected_prediction
    )


def test_metadata_threshold_is_used_and_reported() -> None:
    prediction_service, _ = service(((0.65, 0.35),), threshold=0.37)

    result = prediction_service.predict(feature_input())

    assert result.maintenance_needed_within_90_days_prediction == 0
    assert result.threshold == 0.37


def test_result_is_explicitly_experimental_and_immutable() -> None:
    prediction_service, _ = service(((0.7, 0.3),))

    result = prediction_service.predict(feature_input())

    assert result.experimental is True
    assert result.artifact_schema_version == ARTIFACT_SCHEMA_VERSION
    with pytest.raises(FrozenInstanceError):
        result.threshold = 0.5  # type: ignore[misc]


def test_input_is_not_mutated() -> None:
    prediction_service, _ = service(((0.7, 0.3),))
    inputs = feature_input()
    original = replace(inputs)

    prediction_service.predict(inputs)

    assert inputs == original


@pytest.mark.parametrize(
    "probability_output",
    [(), ((0.5,),), ((0.2, 0.3, 0.5),), ((0.5, 0.5), (0.4, 0.6))],
)
def test_malformed_probability_output_fails_clearly(
    probability_output: Any,
) -> None:
    prediction_service, _ = service(probability_output)

    with pytest.raises(
        ExperimentalMaintenancePredictionError,
        match="one row with two",
    ):
        prediction_service.predict(feature_input())


@pytest.mark.parametrize("probability", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_positive_probability_fails_clearly(probability: float) -> None:
    prediction_service, _ = service(((0.5, probability),))

    with pytest.raises(
        ExperimentalMaintenancePredictionError,
        match="finite and between 0 and 1",
    ):
        prediction_service.predict(feature_input())


def test_incompatible_binary_classes_fail_clearly() -> None:
    prediction_service, _ = service(((0.5, 0.5),), classes=(0, 2))

    with pytest.raises(
        ExperimentalMaintenancePredictionError,
        match="exactly 0 and 1",
    ):
        prediction_service.predict(feature_input())


def test_default_runtime_loader_uses_real_artifact_without_training() -> None:
    if not (
        (DEFAULT_ARTIFACT_DIRECTORY / MODEL_ARTIFACT_FILENAME).is_file()
        and (DEFAULT_ARTIFACT_DIRECTORY / METADATA_FILENAME).is_file()
    ):
        pytest.skip("Local ignored experimental artifact is not present")

    with patch(
        "app.predictive_maintenance_model.train_logistic_regression_model",
        side_effect=AssertionError("Runtime loading must not train"),
    ):
        prediction_service = load_default_experimental_prediction_service()
        result = prediction_service.predict(feature_input())

    assert result.experimental is True
    assert result.threshold == EXPERIMENTAL_DECISION_THRESHOLD


def test_missing_artifact_failure_is_clear(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Model artifact not found"):
        load_default_experimental_prediction_service(tmp_path)
