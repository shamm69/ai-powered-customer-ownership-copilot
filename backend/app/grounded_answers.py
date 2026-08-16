"""Grounded answer generation from approved support-document context."""

from dataclasses import dataclass
from typing import Protocol

from app.retrieval_confidence import (
    RetrievalSupportDecision,
    RetrievalSupportStatus,
)

UNSUPPORTED_ANSWER = (
    "There is insufficient information in the available support documentation "
    "to answer this question."
)


class AnswerGenerator(Protocol):
    """Provider-neutral boundary for generating an answer from one prompt."""

    def generate(self, prompt: str) -> str:
        """Return generated answer text for the supplied grounded prompt."""


@dataclass(frozen=True)
class AnswerSource:
    """Chunk-level source metadata needed for later citations."""

    source_id: str
    document_title: str
    section_title: str
    chunk_id: str


@dataclass(frozen=True)
class GroundedAnswer:
    """An answer paired with its retrieval status and approved sources."""

    answer: str
    retrieval_status: RetrievalSupportStatus
    sources: tuple[AnswerSource, ...]


def generate_grounded_answer(
    question: str,
    retrieval_decision: RetrievalSupportDecision,
    generator: AnswerGenerator | None = None,
) -> GroundedAnswer:
    """Generate from approved context or return the deterministic fallback."""
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("Question must not be empty or blank")

    if retrieval_decision.status is RetrievalSupportStatus.UNSUPPORTED:
        return GroundedAnswer(
            answer=UNSUPPORTED_ANSWER,
            retrieval_status=RetrievalSupportStatus.UNSUPPORTED,
            sources=(),
        )

    if not retrieval_decision.retrieval_results:
        raise ValueError("Supported retrieval must include approved results")
    if generator is None:
        raise ValueError("An answer generator is required for supported retrieval")

    prompt = _build_grounded_prompt(
        normalized_question,
        retrieval_decision,
    )
    generated_answer = generator.generate(prompt)
    if not isinstance(generated_answer, str) or not generated_answer.strip():
        raise ValueError("Answer generator must return nonblank text")

    return GroundedAnswer(
        answer=generated_answer.strip(),
        retrieval_status=RetrievalSupportStatus.SUPPORTED,
        sources=tuple(
            AnswerSource(
                source_id=result.indexed_chunk.chunk.source_id,
                document_title=result.indexed_chunk.chunk.document_title,
                section_title=result.indexed_chunk.chunk.section_title,
                chunk_id=result.indexed_chunk.chunk.chunk_id,
            )
            for result in retrieval_decision.retrieval_results
        ),
    )


def _build_grounded_prompt(
    question: str,
    retrieval_decision: RetrievalSupportDecision,
) -> str:
    context_blocks = []
    for result in retrieval_decision.retrieval_results:
        chunk = result.indexed_chunk.chunk
        context_blocks.append(
            "\n".join(
                (
                    f"Chunk ID: {chunk.chunk_id}",
                    f"Source ID: {chunk.source_id}",
                    f"Title: {chunk.document_title}",
                    f"Section: {chunk.section_title}",
                    "Content:",
                    chunk.content,
                )
            )
        )

    context = "\n\n---\n\n".join(context_blocks)
    return (
        "Answer the automotive support question using only the approved support "
        "context below. Do not invent, infer, or add unsupported factual claims. "
        "If the context does not contain enough information, say that the available "
        "support documentation is insufficient. Cite supporting chunks by their "
        "chunk IDs.\n\n"
        f"Approved support context:\n{context}\n\n"
        f"Question:\n{question}"
    )
