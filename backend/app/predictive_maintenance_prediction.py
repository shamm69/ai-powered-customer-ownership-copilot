"""Application service for experimental maintenance model predictions."""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

from app.predictive_maintenance_artifact import (
    DEFAULT_ARTIFACT_DIRECTORY,
    ExperimentalMaintenanceArtifact,
    load_experimental_maintenance_artifact,
)
from app.predictive_maintenance_data import PREDICTIVE_MAINTENANCE_FEATURE_NAMES


class ExperimentalMaintenancePredictionError(RuntimeError):
    """Raised when the experimental artifact cannot produce a valid result."""


@dataclass(frozen=True)
class PredictiveMaintenanceFeatureInput:
    """Exactly the eight public values accepted by the experimental model."""

    vehicle_age_years: float
    current_odometer_km: float
    distance_since_last_scheduled_service_km: float
    months_since_last_scheduled_service: float
    service_interval_km: float
    service_interval_months: float
    average_monthly_driving_km: float
    usage_severity_score: float

    def __post_init__(self) -> None:
        values = self.as_feature_values()
        if not all(isfinite(value) for value in values):
            raise ValueError("Predictive-maintenance features must be finite")
        if self.vehicle_age_years <= 0:
            raise ValueError("vehicle_age_years must be positive")
        if self.current_odometer_km < 0:
            raise ValueError("current_odometer_km must not be negative")
        if self.distance_since_last_scheduled_service_km < 0:
            raise ValueError(
                "distance_since_last_scheduled_service_km must not be negative"
            )
        if (
            self.distance_since_last_scheduled_service_km
            > self.current_odometer_km
        ):
            raise ValueError(
                "distance since service must not exceed current odometer"
            )
        if self.months_since_last_scheduled_service < 0:
            raise ValueError(
                "months_since_last_scheduled_service must not be negative"
            )
        if self.service_interval_km <= 0 or self.service_interval_months <= 0:
            raise ValueError("service intervals must be positive")
        if self.average_monthly_driving_km <= 0:
            raise ValueError("average_monthly_driving_km must be positive")
        if not 0.0 <= self.usage_severity_score <= 1.0:
            raise ValueError("usage_severity_score must be between 0 and 1")

    def as_feature_values(self) -> tuple[float, ...]:
        """Return values in the persisted artifact's exact feature order."""
        return (
            self.vehicle_age_years,
            self.current_odometer_km,
            self.distance_since_last_scheduled_service_km,
            self.months_since_last_scheduled_service,
            self.service_interval_km,
            self.service_interval_months,
            self.average_monthly_driving_km,
            self.usage_severity_score,
        )


@dataclass(frozen=True)
class ExperimentalMaintenancePrediction:
    """A non-authoritative binary prediction and its probability boundary."""

    maintenance_needed_within_90_days_prediction: int
    positive_class_probability: float
    threshold: float
    experimental: bool
    artifact_schema_version: int


@dataclass(frozen=True)
class ExperimentalMaintenancePredictionService:
    """Injected experimental artifact used for one-snapshot predictions."""

    artifact: ExperimentalMaintenanceArtifact

    def __post_init__(self) -> None:
        metadata = self.artifact.metadata
        if metadata.feature_names != PREDICTIVE_MAINTENANCE_FEATURE_NAMES:
            raise ExperimentalMaintenancePredictionError(
                "Artifact feature ordering is incompatible with prediction input"
            )
        if (
            not isfinite(metadata.decision_threshold)
            or not 0.0 <= metadata.decision_threshold <= 1.0
        ):
            raise ExperimentalMaintenancePredictionError(
                "Artifact threshold must be finite and between 0 and 1"
            )
        if metadata.experimental is not True:
            raise ExperimentalMaintenancePredictionError(
                "Prediction artifact must be marked experimental"
            )

    def predict(
        self,
        feature_input: PredictiveMaintenanceFeatureInput,
    ) -> ExperimentalMaintenancePrediction:
        """Predict the experimental 90-day target using stored metadata."""
        probability_output = self.artifact.pipeline.predict_proba(
            (feature_input.as_feature_values(),)
        )
        positive_probability = _extract_positive_class_probability(
            self.artifact.pipeline,
            probability_output,
        )
        threshold = self.artifact.metadata.decision_threshold
        return ExperimentalMaintenancePrediction(
            maintenance_needed_within_90_days_prediction=int(
                positive_probability >= threshold
            ),
            positive_class_probability=positive_probability,
            threshold=threshold,
            experimental=True,
            artifact_schema_version=self.artifact.metadata.schema_version,
        )


def load_default_experimental_prediction_service(
    artifact_directory: Path = DEFAULT_ARTIFACT_DIRECTORY,
) -> ExperimentalMaintenancePredictionService:
    """Load the existing local artifact without generating or training one."""
    return ExperimentalMaintenancePredictionService(
        artifact=load_experimental_maintenance_artifact(artifact_directory)
    )


def _extract_positive_class_probability(
    pipeline: Any,
    probability_output: Any,
) -> float:
    try:
        classes = tuple(int(value) for value in pipeline.classes_)
    except (AttributeError, TypeError, ValueError) as error:
        raise ExperimentalMaintenancePredictionError(
            "Prediction pipeline must expose binary classes"
        ) from error
    if len(classes) != 2 or set(classes) != {0, 1}:
        raise ExperimentalMaintenancePredictionError(
            "Prediction pipeline classes must be exactly 0 and 1"
        )

    try:
        if len(probability_output) != 1 or len(probability_output[0]) != 2:
            raise ExperimentalMaintenancePredictionError(
                "predict_proba must return one row with two class probabilities"
            )
        positive_probability = float(
            probability_output[0][classes.index(1)]
        )
    except ExperimentalMaintenancePredictionError:
        raise
    except (IndexError, TypeError, ValueError) as error:
        raise ExperimentalMaintenancePredictionError(
            "predict_proba returned malformed probability output"
        ) from error

    if not isfinite(positive_probability) or not 0.0 <= positive_probability <= 1.0:
        raise ExperimentalMaintenancePredictionError(
            "Positive-class probability must be finite and between 0 and 1"
        )
    return positive_probability
