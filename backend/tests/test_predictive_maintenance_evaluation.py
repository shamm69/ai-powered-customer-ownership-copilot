"""Tests for validation threshold selection and final experiment evaluation."""

from dataclasses import FrozenInstanceError
from inspect import signature

import pytest
from sklearn.metrics import average_precision_score, roc_auc_score

from app.predictive_maintenance_baseline import (
    BaselineConfusionMatrix,
    BaselineMetrics,
    DeterministicStatusCounts,
    PredictiveMaintenanceBaselineEvaluation,
)
from app.predictive_maintenance_data import PREDICTIVE_MAINTENANCE_FEATURE_NAMES
from app.predictive_maintenance_evaluation import (
    MINIMUM_USEFUL_F1_IMPROVEMENT,
    THRESHOLD_CANDIDATES,
    ProbabilityModelEvaluation,
    ThresholdCandidateEvaluation,
    binary_predictions_from_probabilities,
    choose_best_threshold_candidate,
    compare_held_out_results,
    confusion_matrix_from_predictions,
    evaluate_probability_model,
    evaluate_useful_value_gate,
    select_validation_threshold,
)
from app.predictive_maintenance_model import ModelValidationMetrics


def baseline_metrics(
    *,
    precision: float = 0.5,
    recall: float = 0.6,
    f1: float = 0.55,
    balanced_accuracy: float = 0.6,
) -> BaselineMetrics:
    return BaselineMetrics(
        accuracy=0.6,
        precision=precision,
        recall=recall,
        f1=f1,
        balanced_accuracy=balanced_accuracy,
    )


def model_metrics(
    *,
    precision: float = 0.6,
    recall: float = 0.7,
    f1: float = 0.65,
    balanced_accuracy: float = 0.7,
    roc_auc: float = 0.75,
) -> ModelValidationMetrics:
    return ModelValidationMetrics(
        accuracy=0.7,
        precision=precision,
        recall=recall,
        f1=f1,
        balanced_accuracy=balanced_accuracy,
        roc_auc=roc_auc,
        average_precision=0.7,
    )


def candidate(
    threshold: float,
    *,
    precision: float,
    recall: float,
    f1: float,
) -> ThresholdCandidateEvaluation:
    return ThresholdCandidateEvaluation(
        threshold=threshold,
        confusion_matrix=BaselineConfusionMatrix(1, 1, 1, 1),
        metrics=baseline_metrics(precision=precision, recall=recall, f1=f1),
    )


def baseline_evaluation(
    *,
    confusion_matrix: BaselineConfusionMatrix,
    metrics: BaselineMetrics,
) -> PredictiveMaintenanceBaselineEvaluation:
    return PredictiveMaintenanceBaselineEvaluation(
        total_rows=sum(
            (
                confusion_matrix.true_positives,
                confusion_matrix.true_negatives,
                confusion_matrix.false_positives,
                confusion_matrix.false_negatives,
            )
        ),
        status_counts=DeterministicStatusCounts(0, 0, 0),
        confusion_matrix=confusion_matrix,
        metrics=metrics,
        predictions=(),
    )


def test_candidate_threshold_grid_is_exact() -> None:
    assert THRESHOLD_CANDIDATES == tuple(value / 100 for value in range(5, 96))
    assert len(THRESHOLD_CANDIDATES) == 91
    assert THRESHOLD_CANDIDATES[0] == 0.05
    assert THRESHOLD_CANDIDATES[-1] == 0.95


def test_threshold_selection_api_accepts_validation_inputs_only() -> None:
    assert tuple(signature(select_validation_threshold).parameters) == (
        "baseline_validation_metrics",
        "validation_targets",
        "validation_probabilities",
    )


def test_candidates_below_required_recall_are_excluded() -> None:
    low_recall = candidate(0.7, precision=0.9, recall=0.59, f1=0.8)
    eligible = candidate(0.4, precision=0.6, recall=0.6, f1=0.6)

    selected = choose_best_threshold_candidate(
        (low_recall, eligible),
        required_recall=0.6,
    )

    assert selected == eligible


def test_highest_f1_eligible_threshold_wins() -> None:
    lower_f1 = candidate(0.3, precision=0.8, recall=0.7, f1=0.65)
    higher_f1 = candidate(0.4, precision=0.7, recall=0.7, f1=0.7)

    assert choose_best_threshold_candidate(
        (lower_f1, higher_f1),
        required_recall=0.6,
    ) == higher_f1


def test_precision_breaks_an_f1_tie() -> None:
    lower_precision = candidate(0.4, precision=0.6, recall=0.8, f1=0.7)
    higher_precision = candidate(0.3, precision=0.7, recall=0.7, f1=0.7)

    assert choose_best_threshold_candidate(
        (lower_precision, higher_precision),
        required_recall=0.6,
    ) == higher_precision


def test_higher_threshold_breaks_final_tie() -> None:
    lower_threshold = candidate(0.4, precision=0.7, recall=0.7, f1=0.7)
    higher_threshold = candidate(0.5, precision=0.7, recall=0.7, f1=0.7)

    assert choose_best_threshold_candidate(
        (lower_threshold, higher_threshold),
        required_recall=0.6,
    ) == higher_threshold


def test_threshold_selection_is_deterministic_and_uses_baseline_recall() -> None:
    targets = (0, 0, 1, 1)
    probabilities = (0.1, 0.4, 0.6, 0.9)
    baseline = baseline_metrics(recall=1.0)

    first = select_validation_threshold(baseline, targets, probabilities)
    second = select_validation_threshold(baseline, targets, probabilities)

    assert first == second
    assert first.required_recall == baseline.recall
    assert first.selected_candidate is not None
    assert first.selected_candidate.metrics.recall >= baseline.recall


def test_no_eligible_threshold_is_reported_explicitly() -> None:
    selected = choose_best_threshold_candidate(
        (candidate(0.5, precision=1.0, recall=0.5, f1=0.6),),
        required_recall=0.9,
    )

    assert selected is None


def test_custom_threshold_converts_ordered_probabilities() -> None:
    assert binary_predictions_from_probabilities(
        (0.19, 0.20, 0.21, 0.90),
        threshold=0.20,
    ) == (0, 1, 1, 1)


def test_confusion_matrix_is_correct() -> None:
    assert confusion_matrix_from_predictions(
        targets=(1, 1, 0, 0),
        predictions=(1, 0, 1, 0),
    ) == BaselineConfusionMatrix(
        true_positives=1,
        true_negatives=1,
        false_positives=1,
        false_negatives=1,
    )


def test_probability_model_metrics_are_correct_on_controlled_fixture() -> None:
    evaluation = evaluate_probability_model(
        targets=(0, 0, 1, 1),
        probabilities=(0.1, 0.6, 0.4, 0.9),
        threshold=0.5,
    )

    assert evaluation.confusion_matrix == BaselineConfusionMatrix(1, 1, 1, 1)
    assert evaluation.metrics.accuracy == 0.5
    assert evaluation.metrics.precision == 0.5
    assert evaluation.metrics.recall == 0.5
    assert evaluation.metrics.f1 == 0.5
    assert evaluation.metrics.balanced_accuracy == 0.5


def test_ranking_metrics_use_probabilities_not_thresholded_labels() -> None:
    targets = (0, 0, 1, 1)
    probabilities = (0.1, 0.6, 0.4, 0.9)
    predictions = binary_predictions_from_probabilities(probabilities, 0.5)

    evaluation = evaluate_probability_model(targets, probabilities, 0.5)

    assert evaluation.metrics.roc_auc == roc_auc_score(targets, probabilities)
    assert evaluation.metrics.average_precision == average_precision_score(
        targets,
        probabilities,
    )
    assert evaluation.metrics.roc_auc != roc_auc_score(targets, predictions)
    assert evaluation.metrics.average_precision != average_precision_score(
        targets,
        predictions,
    )


@pytest.mark.parametrize(
    ("model", "expected_f1", "expected_recall", "expected_roc", "overall"),
    [
        (model_metrics(f1=0.65, recall=0.6, roc_auc=0.70), True, True, True, True),
        (model_metrics(f1=0.64, recall=0.6, roc_auc=0.70), False, True, True, False),
        (model_metrics(f1=0.65, recall=0.59, roc_auc=0.70), True, False, True, False),
        (model_metrics(f1=0.65, recall=0.6, roc_auc=0.69), True, True, False, False),
    ],
)
def test_useful_value_boundaries_and_overall_gate(
    model: ModelValidationMetrics,
    expected_f1: bool,
    expected_recall: bool,
    expected_roc: bool,
    overall: bool,
) -> None:
    baseline = baseline_metrics(recall=0.6, f1=0.6)

    gate = evaluate_useful_value_gate(baseline, model)

    assert MINIMUM_USEFUL_F1_IMPROVEMENT == 0.05
    assert gate.f1_improvement_passed is expected_f1
    assert gate.recall_passed is expected_recall
    assert gate.roc_auc_passed is expected_roc
    assert gate.overall_passed is overall


def test_comparison_differences_are_ml_minus_baseline() -> None:
    baseline = baseline_evaluation(
        confusion_matrix=BaselineConfusionMatrix(6, 7, 3, 4),
        metrics=baseline_metrics(
            precision=0.6,
            recall=0.6,
            f1=0.6,
            balanced_accuracy=0.65,
        ),
    )
    model = ProbabilityModelEvaluation(
        threshold=0.4,
        confusion_matrix=BaselineConfusionMatrix(7, 8, 2, 3),
        metrics=model_metrics(
            precision=0.7,
            recall=0.7,
            f1=0.7,
            balanced_accuracy=0.75,
        ),
    )

    comparison = compare_held_out_results(baseline, model)

    assert comparison.differences.precision_difference == pytest.approx(0.1)
    assert comparison.differences.recall_difference == pytest.approx(0.1)
    assert comparison.differences.f1_difference == pytest.approx(0.1)
    assert comparison.differences.balanced_accuracy_difference == pytest.approx(
        0.1
    )
    assert comparison.differences.false_positive_difference == -1
    assert comparison.differences.false_negative_difference == -1


def test_inputs_are_not_mutated_and_results_are_immutable() -> None:
    targets = (0, 0, 1, 1)
    probabilities = (0.1, 0.4, 0.6, 0.9)
    original_targets = tuple(targets)
    original_probabilities = tuple(probabilities)

    selection = select_validation_threshold(
        baseline_metrics(recall=0.5),
        targets,
        probabilities,
    )

    assert targets == original_targets
    assert probabilities == original_probabilities
    with pytest.raises(FrozenInstanceError):
        selection.required_recall = 0.0  # type: ignore[misc]


def test_established_eight_feature_contract_is_unchanged() -> None:
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
