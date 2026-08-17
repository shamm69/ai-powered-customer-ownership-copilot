"""Side-by-side deterministic and experimental maintenance signals."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from app.maintenance import MaintenanceDueResult, evaluate_maintenance_due_status
from app.predictive_maintenance_artifact import DEFAULT_ARTIFACT_DIRECTORY
from app.predictive_maintenance_baseline import (
    BASELINE_DUE_SOON_THRESHOLD_PERCENT,
    maintenance_status_to_binary,
)
from app.predictive_maintenance_prediction import (
    ExperimentalMaintenancePrediction,
    PredictiveMaintenanceFeatureInput,
    load_default_experimental_prediction_service,
)


class ExperimentalMaintenancePredictor(Protocol):
    """Capability required from the existing experimental prediction service."""

    def predict(
        self,
        feature_input: PredictiveMaintenanceFeatureInput,
    ) -> ExperimentalMaintenancePrediction:
        """Return one experimental 90-day prediction."""
        ...


class MaintenanceSignalRelationship(str, Enum):
    """All possible relationships between the two binary comparison signals."""

    AGREE_NEGATIVE = "agree_negative"
    AGREE_POSITIVE = "agree_positive"
    DETERMINISTIC_ONLY_POSITIVE = "deterministic_only_positive"
    ML_ONLY_POSITIVE = "ml_only_positive"


@dataclass(frozen=True)
class MaintenancePredictionComparison:
    """Distinct authoritative and experimental results with no merged decision."""

    deterministic_result: MaintenanceDueResult
    experimental_result: ExperimentalMaintenancePrediction
    deterministic_binary_signal: int
    experimental_ml_binary_signal: int
    relationship: MaintenanceSignalRelationship


@dataclass(frozen=True)
class MaintenancePredictionComparisonService:
    """Run the existing deterministic evaluator and injected ML predictor."""

    experimental_predictor: ExperimentalMaintenancePredictor

    def compare(
        self,
        feature_input: PredictiveMaintenanceFeatureInput,
    ) -> MaintenancePredictionComparison:
        """Return both signals side by side without creating a hybrid result."""
        last_service_odometer_km = (
            feature_input.current_odometer_km
            - feature_input.distance_since_last_scheduled_service_km
        )
        deterministic_result = evaluate_maintenance_due_status(
            current_odometer_km=feature_input.current_odometer_km,
            last_service_odometer_km=last_service_odometer_km,
            months_since_last_service=(
                feature_input.months_since_last_scheduled_service
            ),
            service_interval_km=feature_input.service_interval_km,
            service_interval_months=feature_input.service_interval_months,
            due_soon_threshold_percent=BASELINE_DUE_SOON_THRESHOLD_PERCENT,
        )
        experimental_result = self.experimental_predictor.predict(feature_input)
        deterministic_signal = maintenance_status_to_binary(
            deterministic_result.status
        )
        experimental_signal = (
            experimental_result.maintenance_needed_within_90_days_prediction
        )
        return MaintenancePredictionComparison(
            deterministic_result=deterministic_result,
            experimental_result=experimental_result,
            deterministic_binary_signal=deterministic_signal,
            experimental_ml_binary_signal=experimental_signal,
            relationship=classify_signal_relationship(
                deterministic_signal,
                experimental_signal,
            ),
        )


def classify_signal_relationship(
    deterministic_binary_signal: int,
    experimental_ml_binary_signal: int,
) -> MaintenanceSignalRelationship:
    """Classify agreement or disagreement without choosing a final signal."""
    signals = (deterministic_binary_signal, experimental_ml_binary_signal)
    if any(signal not in (0, 1) for signal in signals):
        raise ValueError("Comparison signals must be binary values")
    relationships = {
        (0, 0): MaintenanceSignalRelationship.AGREE_NEGATIVE,
        (1, 1): MaintenanceSignalRelationship.AGREE_POSITIVE,
        (1, 0): MaintenanceSignalRelationship.DETERMINISTIC_ONLY_POSITIVE,
        (0, 1): MaintenanceSignalRelationship.ML_ONLY_POSITIVE,
    }
    return relationships[signals]


def load_default_maintenance_prediction_comparison_service(
    artifact_directory: Path = DEFAULT_ARTIFACT_DIRECTORY,
) -> MaintenancePredictionComparisonService:
    """Compose the comparison service from an existing local artifact."""
    return MaintenancePredictionComparisonService(
        experimental_predictor=load_default_experimental_prediction_service(
            artifact_directory
        )
    )
