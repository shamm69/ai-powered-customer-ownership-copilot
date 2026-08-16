"""Deterministic support decisions for semantic retrieval results."""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from numbers import Real

from app.document_retrieval import RetrievalResult


class RetrievalSupportStatus(str, Enum):
    """Whether retrieved context is relevant enough for later use."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class RetrievalSupportDecision:
    """An immutable retrieval-support decision with explainable scores."""

    status: RetrievalSupportStatus
    retrieval_results: tuple[RetrievalResult, ...]
    best_similarity_score: float | None
    minimum_similarity: float


def assess_retrieval_support(
    retrieval_results: Iterable[RetrievalResult],
    minimum_similarity: float,
) -> RetrievalSupportDecision:
    """Accept ranked retrieval context when its top score meets the threshold."""
    threshold = _validate_minimum_similarity(minimum_similarity)
    ordered_results = tuple(retrieval_results)
    if not ordered_results:
        return RetrievalSupportDecision(
            status=RetrievalSupportStatus.UNSUPPORTED,
            retrieval_results=(),
            best_similarity_score=None,
            minimum_similarity=threshold,
        )

    if any(
        not math.isfinite(result.similarity_score) for result in ordered_results
    ):
        raise ValueError("Retrieval similarity scores must be finite")

    best_similarity_score = ordered_results[0].similarity_score
    if best_similarity_score >= threshold:
        return RetrievalSupportDecision(
            status=RetrievalSupportStatus.SUPPORTED,
            retrieval_results=ordered_results,
            best_similarity_score=best_similarity_score,
            minimum_similarity=threshold,
        )

    return RetrievalSupportDecision(
        status=RetrievalSupportStatus.UNSUPPORTED,
        retrieval_results=(),
        best_similarity_score=best_similarity_score,
        minimum_similarity=threshold,
    )


def _validate_minimum_similarity(minimum_similarity: float) -> float:
    if isinstance(minimum_similarity, bool) or not isinstance(
        minimum_similarity, Real
    ):
        raise ValueError("minimum_similarity must be a finite number")

    threshold = float(minimum_similarity)
    if not math.isfinite(threshold):
        raise ValueError("minimum_similarity must be a finite number")
    if not -1.0 <= threshold <= 1.0:
        raise ValueError("minimum_similarity must be between -1.0 and 1.0")
    return threshold
