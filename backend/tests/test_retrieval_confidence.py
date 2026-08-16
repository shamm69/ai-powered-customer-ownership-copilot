"""Tests for retrieval confidence and unsupported-query decisions."""

from dataclasses import FrozenInstanceError

import pytest

from app.document_chunking import DocumentChunk
from app.document_embeddings import IndexedDocumentChunk
from app.document_retrieval import RetrievalResult
from app.retrieval_confidence import (
    RetrievalSupportDecision,
    RetrievalSupportStatus,
    assess_retrieval_support,
)


def make_retrieval_result(
    chunk_id: str,
    similarity_score: float,
) -> RetrievalResult:
    indexed_chunk = IndexedDocumentChunk(
        chunk=DocumentChunk(
            chunk_id=chunk_id,
            source_id="support.md",
            document_title="Support Guide",
            section_title="Support Section",
            content="Generic support guidance.",
        ),
        embedding=(1.0, 0.0),
    )
    return RetrievalResult(
        indexed_chunk=indexed_chunk,
        similarity_score=similarity_score,
    )


def test_supported_decision_preserves_all_ordered_retrieval_results() -> None:
    results = (
        make_retrieval_result("support.md::chunk-001", 0.82),
        make_retrieval_result("support.md::chunk-002", 0.71),
    )

    decision = assess_retrieval_support(results, minimum_similarity=0.75)

    assert decision == RetrievalSupportDecision(
        status=RetrievalSupportStatus.SUPPORTED,
        retrieval_results=results,
        best_similarity_score=0.82,
        minimum_similarity=0.75,
    )


def test_similarity_equal_to_threshold_is_supported() -> None:
    result = make_retrieval_result("support.md::chunk-001", 0.75)

    decision = assess_retrieval_support((result,), minimum_similarity=0.75)

    assert decision.status is RetrievalSupportStatus.SUPPORTED
    assert decision.retrieval_results == (result,)


def test_score_below_threshold_is_unsupported_without_context() -> None:
    result = make_retrieval_result("support.md::chunk-001", 0.74)

    decision = assess_retrieval_support((result,), minimum_similarity=0.75)

    assert decision.status is RetrievalSupportStatus.UNSUPPORTED
    assert decision.retrieval_results == ()
    assert decision.best_similarity_score == 0.74
    assert decision.minimum_similarity == 0.75


def test_empty_retrieval_results_are_unsupported() -> None:
    decision = assess_retrieval_support((), minimum_similarity=0.5)

    assert decision == RetrievalSupportDecision(
        status=RetrievalSupportStatus.UNSUPPORTED,
        retrieval_results=(),
        best_similarity_score=None,
        minimum_similarity=0.5,
    )


@pytest.mark.parametrize("minimum_similarity", [-1.0, 0.0, 1.0])
def test_valid_threshold_boundaries_are_accepted(
    minimum_similarity: float,
) -> None:
    result = make_retrieval_result("support.md::chunk-001", 1.0)

    decision = assess_retrieval_support(
        (result,), minimum_similarity=minimum_similarity
    )

    assert decision.status is RetrievalSupportStatus.SUPPORTED
    assert decision.minimum_similarity == minimum_similarity


@pytest.mark.parametrize(
    "minimum_similarity",
    [-1.01, 1.01, float("nan"), float("inf"), float("-inf"), True, "0.5"],
)
def test_invalid_threshold_is_rejected(minimum_similarity: object) -> None:
    with pytest.raises(ValueError, match="minimum_similarity"):
        assess_retrieval_support(
            (),
            minimum_similarity=minimum_similarity,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("similarity_score", [float("nan"), float("inf")])
def test_non_finite_retrieval_score_is_rejected(
    similarity_score: float,
) -> None:
    result = make_retrieval_result(
        "support.md::chunk-001",
        similarity_score,
    )

    with pytest.raises(ValueError, match="similarity scores must be finite"):
        assess_retrieval_support((result,), minimum_similarity=0.5)


def test_support_decision_is_immutable() -> None:
    decision = assess_retrieval_support((), minimum_similarity=0.5)

    with pytest.raises(FrozenInstanceError):
        decision.minimum_similarity = 0.4  # type: ignore[misc]
