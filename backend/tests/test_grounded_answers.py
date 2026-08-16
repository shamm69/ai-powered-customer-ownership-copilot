"""Tests for grounded answer generation from approved retrieval context."""

from dataclasses import FrozenInstanceError

import pytest

from app.document_chunking import DocumentChunk
from app.document_embeddings import IndexedDocumentChunk
from app.document_retrieval import RetrievalResult
from app.grounded_answers import (
    UNSUPPORTED_ANSWER,
    AnswerSource,
    GroundedAnswer,
    generate_grounded_answer,
)
from app.retrieval_confidence import (
    RetrievalSupportDecision,
    RetrievalSupportStatus,
)


class FakeAnswerGenerator:
    def __init__(self, answer: object) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer  # type: ignore[return-value]


def make_retrieval_result(
    *,
    chunk_id: str,
    source_id: str,
    title: str,
    section: str,
    content: str,
    score: float,
) -> RetrievalResult:
    return RetrievalResult(
        indexed_chunk=IndexedDocumentChunk(
            chunk=DocumentChunk(
                chunk_id=chunk_id,
                source_id=source_id,
                document_title=title,
                section_title=section,
                content=content,
            ),
            embedding=(1.0, 0.0),
        ),
        similarity_score=score,
    )


def make_supported_decision() -> RetrievalSupportDecision:
    results = (
        make_retrieval_result(
            chunk_id="maintenance.md::chunk-001",
            source_id="maintenance.md",
            title="Maintenance Guide",
            section="Service Intervals",
            content="Follow both the distance and time service intervals.",
            score=0.9,
        ),
        make_retrieval_result(
            chunk_id="warning-lights.md::chunk-002",
            source_id="warning-lights.md",
            title="Warning Lights",
            section="Red Warning Lights",
            content="Stop safely when a red warning light indicates danger.",
            score=0.8,
        ),
    )
    return RetrievalSupportDecision(
        status=RetrievalSupportStatus.SUPPORTED,
        retrieval_results=results,
        best_similarity_score=0.9,
        minimum_similarity=0.7,
    )


def make_unsupported_decision() -> RetrievalSupportDecision:
    return RetrievalSupportDecision(
        status=RetrievalSupportStatus.UNSUPPORTED,
        retrieval_results=(),
        best_similarity_score=0.3,
        minimum_similarity=0.7,
    )


def test_unsupported_retrieval_returns_fallback_without_generator() -> None:
    result = generate_grounded_answer(
        "What support information is available?",
        make_unsupported_decision(),
    )

    assert result == GroundedAnswer(
        answer=UNSUPPORTED_ANSWER,
        retrieval_status=RetrievalSupportStatus.UNSUPPORTED,
        sources=(),
    )


def test_unsupported_retrieval_does_not_call_generator() -> None:
    generator = FakeAnswerGenerator("This must not be used.")

    generate_grounded_answer(
        "What support information is available?",
        make_unsupported_decision(),
        generator,
    )

    assert generator.prompts == []


def test_supported_retrieval_generates_answer_from_approved_context() -> None:
    generator = FakeAnswerGenerator("Use both distance and time intervals.")

    result = generate_grounded_answer(
        "  When should service be performed?  ",
        make_supported_decision(),
        generator,
    )

    assert result.answer == "Use both distance and time intervals."
    assert result.retrieval_status is RetrievalSupportStatus.SUPPORTED
    assert len(generator.prompts) == 1
    prompt = generator.prompts[0]
    assert "Question:\nWhen should service be performed?" in prompt
    assert "using only the approved support context" in prompt
    assert "Do not invent, infer, or add unsupported factual claims" in prompt
    assert "maintenance.md::chunk-001" in prompt
    assert "Follow both the distance and time service intervals." in prompt
    assert "warning-lights.md::chunk-002" in prompt
    assert "Stop safely when a red warning light indicates danger." in prompt


def test_supported_answer_preserves_ordered_chunk_source_metadata() -> None:
    result = generate_grounded_answer(
        "When should service be performed?",
        make_supported_decision(),
        FakeAnswerGenerator("Follow the documented service intervals."),
    )

    assert result.sources == (
        AnswerSource(
            source_id="maintenance.md",
            document_title="Maintenance Guide",
            section_title="Service Intervals",
            chunk_id="maintenance.md::chunk-001",
        ),
        AnswerSource(
            source_id="warning-lights.md",
            document_title="Warning Lights",
            section_title="Red Warning Lights",
            chunk_id="warning-lights.md::chunk-002",
        ),
    )


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
def test_blank_question_is_rejected(question: str) -> None:
    with pytest.raises(ValueError, match="Question must not be empty or blank"):
        generate_grounded_answer(question, make_unsupported_decision())


@pytest.mark.parametrize("generated_answer", ["", "   ", None, 42])
def test_blank_or_malformed_generated_answer_is_rejected(
    generated_answer: object,
) -> None:
    with pytest.raises(ValueError, match="must return nonblank text"):
        generate_grounded_answer(
            "When should service be performed?",
            make_supported_decision(),
            FakeAnswerGenerator(generated_answer),
        )


def test_supported_retrieval_requires_approved_results() -> None:
    malformed_decision = RetrievalSupportDecision(
        status=RetrievalSupportStatus.SUPPORTED,
        retrieval_results=(),
        best_similarity_score=None,
        minimum_similarity=0.7,
    )

    with pytest.raises(ValueError, match="must include approved results"):
        generate_grounded_answer(
            "When should service be performed?",
            malformed_decision,
            FakeAnswerGenerator("Answer."),
        )


def test_supported_retrieval_requires_generator() -> None:
    with pytest.raises(ValueError, match="answer generator is required"):
        generate_grounded_answer(
            "When should service be performed?",
            make_supported_decision(),
        )


def test_grounded_answer_and_source_are_immutable() -> None:
    result = generate_grounded_answer(
        "When should service be performed?",
        make_supported_decision(),
        FakeAnswerGenerator("Follow the documented intervals."),
    )

    with pytest.raises(FrozenInstanceError):
        result.answer = "Changed."  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.sources[0].chunk_id = "changed"  # type: ignore[misc]
