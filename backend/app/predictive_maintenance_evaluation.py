"""Validation threshold selection and held-out experiment comparison."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

from sklearn.metrics import average_precision_score, roc_auc_score

from app.predictive_maintenance_baseline import (
    BaselineConfusionMatrix,
    BaselineMetrics,
    PredictiveMaintenanceBaselineEvaluation,
    calculate_baseline_metrics,
)
from app.predictive_maintenance_model import ModelValidationMetrics

THRESHOLD_CANDIDATES: tuple[float, ...] = tuple(
    value / 100 for value in range(5, 96)
)
MINIMUM_USEFUL_F1_IMPROVEMENT = 0.05
MINIMUM_USEFUL_ROC_AUC = 0.70


@dataclass(frozen=True)
class ThresholdCandidateEvaluation:
    """Thresholded validation performance for one candidate."""

    threshold: float
    confusion_matrix: BaselineConfusionMatrix
    metrics: BaselineMetrics


@dataclass(frozen=True)
class ThresholdSelectionResult:
    """Deterministic validation-only threshold-selection outcome."""

    required_recall: float
    candidates: tuple[ThresholdCandidateEvaluation, ...]
    selected_candidate: ThresholdCandidateEvaluation | None


@dataclass(frozen=True)
class ProbabilityModelEvaluation:
    """Threshold and probability metrics for one labeled partition."""

    threshold: float
    confusion_matrix: BaselineConfusionMatrix
    metrics: ModelValidationMetrics


@dataclass(frozen=True)
class UsefulValueGate:
    """Frozen test-set criteria for whether ML adds useful value."""

    f1_improvement_passed: bool
    recall_passed: bool
    roc_auc_passed: bool
    overall_passed: bool


@dataclass(frozen=True)
class ComparisonDifferences:
    """ML-minus-baseline metric and error-count differences."""

    precision_difference: float
    recall_difference: float
    f1_difference: float
    balanced_accuracy_difference: float
    false_positive_difference: int
    false_negative_difference: int


@dataclass(frozen=True)
class FinalPredictiveMaintenanceComparison:
    """Held-out baseline/ML results and the frozen useful-value decision."""

    baseline: PredictiveMaintenanceBaselineEvaluation
    model: ProbabilityModelEvaluation
    differences: ComparisonDifferences
    useful_value_gate: UsefulValueGate


def binary_predictions_from_probabilities(
    probabilities: Sequence[float],
    threshold: float,
) -> tuple[int, ...]:
    """Apply an inclusive classification threshold to ordered probabilities."""
    _validate_threshold(threshold)
    _validate_probabilities(probabilities)
    return tuple(int(probability >= threshold) for probability in probabilities)


def confusion_matrix_from_predictions(
    targets: Sequence[int],
    predictions: Sequence[int],
) -> BaselineConfusionMatrix:
    """Build a binary confusion matrix with maintenance-needed as positive."""
    if len(targets) != len(predictions) or not targets:
        raise ValueError("Targets and predictions must be nonempty and equal in length")
    if any(target not in (0, 1) for target in targets):
        raise ValueError("Targets must be binary")
    if any(prediction not in (0, 1) for prediction in predictions):
        raise ValueError("Predictions must be binary")

    return BaselineConfusionMatrix(
        true_positives=sum(
            target == 1 and prediction == 1
            for target, prediction in zip(targets, predictions, strict=True)
        ),
        true_negatives=sum(
            target == 0 and prediction == 0
            for target, prediction in zip(targets, predictions, strict=True)
        ),
        false_positives=sum(
            target == 0 and prediction == 1
            for target, prediction in zip(targets, predictions, strict=True)
        ),
        false_negatives=sum(
            target == 1 and prediction == 0
            for target, prediction in zip(targets, predictions, strict=True)
        ),
    )


def select_validation_threshold(
    baseline_validation_metrics: BaselineMetrics,
    validation_targets: Sequence[int],
    validation_probabilities: Sequence[float],
) -> ThresholdSelectionResult:
    """Choose a threshold using only validation results and the frozen rule."""
    if len(validation_targets) != len(validation_probabilities):
        raise ValueError("Validation targets and probabilities must have equal length")

    candidates = tuple(
        _evaluate_threshold_candidate(
            validation_targets,
            validation_probabilities,
            threshold,
        )
        for threshold in THRESHOLD_CANDIDATES
    )
    selected_candidate = choose_best_threshold_candidate(
        candidates,
        required_recall=baseline_validation_metrics.recall,
    )
    return ThresholdSelectionResult(
        required_recall=baseline_validation_metrics.recall,
        candidates=candidates,
        selected_candidate=selected_candidate,
    )


def choose_best_threshold_candidate(
    candidates: Sequence[ThresholdCandidateEvaluation],
    required_recall: float,
) -> ThresholdCandidateEvaluation | None:
    """Apply recall eligibility, then F1, precision, and threshold tie-breaks."""
    eligible = tuple(
        candidate
        for candidate in candidates
        if candidate.metrics.recall >= required_recall
    )
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda candidate: (
            candidate.metrics.f1,
            candidate.metrics.precision,
            candidate.threshold,
        ),
    )


def evaluate_probability_model(
    targets: Sequence[int],
    probabilities: Sequence[float],
    threshold: float,
) -> ProbabilityModelEvaluation:
    """Evaluate thresholded errors and continuous probability ranking."""
    predictions = binary_predictions_from_probabilities(probabilities, threshold)
    confusion_matrix = confusion_matrix_from_predictions(targets, predictions)
    threshold_metrics = calculate_baseline_metrics(confusion_matrix)
    return ProbabilityModelEvaluation(
        threshold=threshold,
        confusion_matrix=confusion_matrix,
        metrics=ModelValidationMetrics(
            accuracy=threshold_metrics.accuracy,
            precision=threshold_metrics.precision,
            recall=threshold_metrics.recall,
            f1=threshold_metrics.f1,
            balanced_accuracy=threshold_metrics.balanced_accuracy,
            roc_auc=float(roc_auc_score(targets, probabilities)),
            average_precision=float(average_precision_score(targets, probabilities)),
        ),
    )


def compare_held_out_results(
    baseline: PredictiveMaintenanceBaselineEvaluation,
    model: ProbabilityModelEvaluation,
) -> FinalPredictiveMaintenanceComparison:
    """Compare frozen held-out results without changing either system."""
    differences = ComparisonDifferences(
        precision_difference=model.metrics.precision - baseline.metrics.precision,
        recall_difference=model.metrics.recall - baseline.metrics.recall,
        f1_difference=model.metrics.f1 - baseline.metrics.f1,
        balanced_accuracy_difference=(
            model.metrics.balanced_accuracy - baseline.metrics.balanced_accuracy
        ),
        false_positive_difference=(
            model.confusion_matrix.false_positives
            - baseline.confusion_matrix.false_positives
        ),
        false_negative_difference=(
            model.confusion_matrix.false_negatives
            - baseline.confusion_matrix.false_negatives
        ),
    )
    return FinalPredictiveMaintenanceComparison(
        baseline=baseline,
        model=model,
        differences=differences,
        useful_value_gate=evaluate_useful_value_gate(baseline.metrics, model.metrics),
    )


def evaluate_useful_value_gate(
    baseline_metrics: BaselineMetrics,
    model_metrics: ModelValidationMetrics,
) -> UsefulValueGate:
    """Apply the frozen held-out useful-value criteria exactly."""
    f1_passed = (
        model_metrics.f1
        >= baseline_metrics.f1 + MINIMUM_USEFUL_F1_IMPROVEMENT
    )
    recall_passed = model_metrics.recall >= baseline_metrics.recall
    roc_auc_passed = model_metrics.roc_auc >= MINIMUM_USEFUL_ROC_AUC
    return UsefulValueGate(
        f1_improvement_passed=f1_passed,
        recall_passed=recall_passed,
        roc_auc_passed=roc_auc_passed,
        overall_passed=f1_passed and recall_passed and roc_auc_passed,
    )


def _evaluate_threshold_candidate(
    targets: Sequence[int],
    probabilities: Sequence[float],
    threshold: float,
) -> ThresholdCandidateEvaluation:
    predictions = binary_predictions_from_probabilities(probabilities, threshold)
    confusion_matrix = confusion_matrix_from_predictions(targets, predictions)
    return ThresholdCandidateEvaluation(
        threshold=threshold,
        confusion_matrix=confusion_matrix,
        metrics=calculate_baseline_metrics(confusion_matrix),
    )


def _validate_threshold(threshold: float) -> None:
    if not isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be finite and between 0 and 1")


def _validate_probabilities(probabilities: Sequence[float]) -> None:
    if not probabilities:
        raise ValueError("At least one probability is required")
    if any(
        not isfinite(probability) or not 0.0 <= probability <= 1.0
        for probability in probabilities
    ):
        raise ValueError("Probabilities must be finite and between 0 and 1")
