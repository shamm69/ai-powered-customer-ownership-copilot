"""Lightweight analysis for synthetic predictive-maintenance snapshots."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations
from math import sqrt
from statistics import fmean, median, pstdev

from app.predictive_maintenance_data import (
    PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
    PredictiveMaintenanceSnapshot,
    extract_predictive_maintenance_features,
)

CLASS_IMBALANCE_MINORITY_RATE_THRESHOLD = 0.10
NEAR_ZERO_STANDARD_DEVIATION_THRESHOLD = 1e-9
EXTREME_FEATURE_CORRELATION_THRESHOLD = 0.95
EXTREME_TARGET_CORRELATION_THRESHOLD = 0.80


@dataclass(frozen=True)
class FeatureSummary:
    """Descriptive statistics for one model feature."""

    minimum: float
    maximum: float
    mean: float
    standard_deviation: float
    median: float


@dataclass(frozen=True)
class FeatureAnalysis:
    """Overall and per-class statistics for one model feature."""

    name: str
    summary: FeatureSummary
    negative_class_mean: float | None
    positive_class_mean: float | None
    target_correlation: float | None


@dataclass(frozen=True)
class PairwiseFeatureCorrelation:
    """Pearson correlation between two model features."""

    first_feature: str
    second_feature: str
    correlation: float | None


@dataclass(frozen=True)
class AnalysisFinding:
    """A conservative warning about potentially suspicious dataset behaviour."""

    code: str
    message: str


@dataclass(frozen=True)
class PredictiveMaintenanceDatasetAnalysis:
    """Immutable reusable analysis of a synthetic snapshot collection."""

    total_rows: int
    positive_count: int
    negative_count: int
    positive_rate: float
    feature_analyses: tuple[FeatureAnalysis, ...]
    feature_correlations: tuple[PairwiseFeatureCorrelation, ...]
    findings: tuple[AnalysisFinding, ...]


def analyze_predictive_maintenance_snapshots(
    snapshots: Iterable[PredictiveMaintenanceSnapshot],
) -> PredictiveMaintenanceDatasetAnalysis:
    """Summarize public model features, class tendencies, and correlations."""
    rows = tuple(snapshots)
    if not rows:
        raise ValueError("At least one predictive-maintenance snapshot is required")

    feature_rows = tuple(
        extract_predictive_maintenance_features(snapshot) for snapshot in rows
    )
    targets = tuple(
        float(snapshot.maintenance_needed_within_90_days) for snapshot in rows
    )
    positive_count = int(sum(targets))
    negative_count = len(rows) - positive_count

    feature_columns = tuple(
        tuple(feature_row[index] for feature_row in feature_rows)
        for index in range(len(PREDICTIVE_MAINTENANCE_FEATURE_NAMES))
    )
    feature_analyses = tuple(
        _analyze_feature(name, values, targets)
        for name, values in zip(
            PREDICTIVE_MAINTENANCE_FEATURE_NAMES,
            feature_columns,
            strict=True,
        )
    )
    feature_correlations = tuple(
        PairwiseFeatureCorrelation(
            first_feature=PREDICTIVE_MAINTENANCE_FEATURE_NAMES[first_index],
            second_feature=PREDICTIVE_MAINTENANCE_FEATURE_NAMES[second_index],
            correlation=_pearson_correlation(
                feature_columns[first_index],
                feature_columns[second_index],
            ),
        )
        for first_index, second_index in combinations(
            range(len(PREDICTIVE_MAINTENANCE_FEATURE_NAMES)),
            2,
        )
    )
    findings = _build_findings(
        total_rows=len(rows),
        positive_count=positive_count,
        negative_count=negative_count,
        feature_analyses=feature_analyses,
        feature_correlations=feature_correlations,
    )

    return PredictiveMaintenanceDatasetAnalysis(
        total_rows=len(rows),
        positive_count=positive_count,
        negative_count=negative_count,
        positive_rate=positive_count / len(rows),
        feature_analyses=feature_analyses,
        feature_correlations=feature_correlations,
        findings=findings,
    )


def _analyze_feature(
    name: str,
    values: Sequence[float],
    targets: Sequence[float],
) -> FeatureAnalysis:
    negative_values = tuple(
        value for value, target in zip(values, targets, strict=True) if target == 0
    )
    positive_values = tuple(
        value for value, target in zip(values, targets, strict=True) if target == 1
    )
    return FeatureAnalysis(
        name=name,
        summary=FeatureSummary(
            minimum=min(values),
            maximum=max(values),
            mean=fmean(values),
            standard_deviation=pstdev(values),
            median=median(values),
        ),
        negative_class_mean=fmean(negative_values) if negative_values else None,
        positive_class_mean=fmean(positive_values) if positive_values else None,
        target_correlation=_pearson_correlation(values, targets),
    )


def _pearson_correlation(
    first_values: Sequence[float],
    second_values: Sequence[float],
) -> float | None:
    """Return Pearson correlation, or None when either input has no variance."""
    if len(first_values) != len(second_values) or not first_values:
        raise ValueError("Correlation inputs must be nonempty and equal in length")

    first_mean = fmean(first_values)
    second_mean = fmean(second_values)
    first_deviations = tuple(value - first_mean for value in first_values)
    second_deviations = tuple(value - second_mean for value in second_values)
    first_sum_squares = sum(value * value for value in first_deviations)
    second_sum_squares = sum(value * value for value in second_deviations)
    if first_sum_squares == 0.0 or second_sum_squares == 0.0:
        return None

    cross_product = sum(
        first * second
        for first, second in zip(
            first_deviations,
            second_deviations,
            strict=True,
        )
    )
    return cross_product / sqrt(first_sum_squares * second_sum_squares)


def _build_findings(
    *,
    total_rows: int,
    positive_count: int,
    negative_count: int,
    feature_analyses: tuple[FeatureAnalysis, ...],
    feature_correlations: tuple[PairwiseFeatureCorrelation, ...],
) -> tuple[AnalysisFinding, ...]:
    findings: list[AnalysisFinding] = []
    minority_rate = min(positive_count, negative_count) / total_rows
    if minority_rate < CLASS_IMBALANCE_MINORITY_RATE_THRESHOLD:
        findings.append(
            AnalysisFinding(
                code="pathological_class_imbalance",
                message=(
                    f"Minority class rate {minority_rate:.3f} is below "
                    f"{CLASS_IMBALANCE_MINORITY_RATE_THRESHOLD:.3f}."
                ),
            )
        )

    for feature in feature_analyses:
        if (
            feature.summary.standard_deviation
            <= NEAR_ZERO_STANDARD_DEVIATION_THRESHOLD
        ):
            findings.append(
                AnalysisFinding(
                    code="near_zero_variance_feature",
                    message=f"{feature.name} has near-zero variance.",
                )
            )
        if (
            feature.target_correlation is not None
            and abs(feature.target_correlation)
            >= EXTREME_TARGET_CORRELATION_THRESHOLD
        ):
            findings.append(
                AnalysisFinding(
                    code="extreme_feature_target_correlation",
                    message=(
                        f"{feature.name} has target correlation "
                        f"{feature.target_correlation:.3f}."
                    ),
                )
            )

    for correlation in feature_correlations:
        if (
            correlation.correlation is not None
            and abs(correlation.correlation)
            >= EXTREME_FEATURE_CORRELATION_THRESHOLD
        ):
            findings.append(
                AnalysisFinding(
                    code="extreme_feature_feature_correlation",
                    message=(
                        f"{correlation.first_feature} and "
                        f"{correlation.second_feature} have correlation "
                        f"{correlation.correlation:.3f}."
                    ),
                )
            )

    return tuple(findings)
