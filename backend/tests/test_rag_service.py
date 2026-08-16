"""Tests for the application-layer RAG pipeline service."""

from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.grounded_answers import UNSUPPORTED_ANSWER
from app.rag_service import prepare_rag_service
from app.retrieval_confidence import RetrievalSupportStatus


class FakeTextEmbedder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def embed_texts(
        self,
        texts: Sequence[str],
    ) -> tuple[tuple[float, ...], ...]:
        self.calls.append(tuple(texts))
        return tuple(self._embedding_for(text) for text in texts)

    @staticmethod
    def _embedding_for(text: str) -> tuple[float, ...]:
        normalized_text = text.lower()
        if "unrelated paint color" in normalized_text:
            return (-1.0, -1.0)
        if "roadside" in normalized_text:
            return (0.0, 1.0)
        return (1.0, 0.0)


class FakeAnswerGenerator:
    def __init__(self, answer: str = "Follow the documented service intervals.") -> None:
        self.answer = answer
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer


@pytest.fixture
def support_corpus(tmp_path: Path) -> Path:
    (tmp_path / "maintenance.md").write_text(
        "# Maintenance Guide\n\n"
        "Follow both distance and time service intervals.",
        encoding="utf-8",
    )
    (tmp_path / "roadside.md").write_text(
        "# Roadside Guide\n\n"
        "Contact roadside assistance when a vehicle cannot be driven safely.",
        encoding="utf-8",
    )
    return tmp_path


def test_preparation_loads_chunks_and_builds_index_once(
    support_corpus: Path,
) -> None:
    embedder = FakeTextEmbedder()
    service = prepare_rag_service(
        embedder,
        FakeAnswerGenerator(),
        top_k=1,
        minimum_similarity=0.75,
        corpus_directory=support_corpus,
    )

    assert [item.chunk.chunk_id for item in service.indexed_chunks] == [
        "maintenance.md::chunk-001",
        "roadside.md::chunk-001",
    ]
    assert embedder.calls == [
        (
            "Follow both distance and time service intervals.",
            "Contact roadside assistance when a vehicle cannot be driven safely.",
        )
    ]


def test_supported_question_runs_complete_pipeline_and_preserves_source(
    support_corpus: Path,
) -> None:
    embedder = FakeTextEmbedder()
    generator = FakeAnswerGenerator()
    service = prepare_rag_service(
        embedder,
        generator,
        top_k=1,
        minimum_similarity=0.75,
        corpus_directory=support_corpus,
    )

    answer = service.answer_question("When should scheduled service occur?")

    assert answer.answer == "Follow the documented service intervals."
    assert answer.retrieval_status is RetrievalSupportStatus.SUPPORTED
    assert len(answer.sources) == 1
    assert answer.sources[0].source_id == "maintenance.md"
    assert answer.sources[0].document_title == "Maintenance Guide"
    assert answer.sources[0].section_title == "Maintenance Guide"
    assert answer.sources[0].chunk_id == "maintenance.md::chunk-001"
    assert len(generator.prompts) == 1
    assert "When should scheduled service occur?" in generator.prompts[0]
    assert "Follow both distance and time service intervals." in generator.prompts[0]
    assert "roadside assistance" not in generator.prompts[0]


def test_unsupported_question_returns_fallback_without_calling_generator(
    support_corpus: Path,
) -> None:
    generator = FakeAnswerGenerator()
    service = prepare_rag_service(
        FakeTextEmbedder(),
        generator,
        top_k=2,
        minimum_similarity=0.5,
        corpus_directory=support_corpus,
    )

    answer = service.answer_question("What unrelated paint color is available?")

    assert answer.answer == UNSUPPORTED_ANSWER
    assert answer.retrieval_status is RetrievalSupportStatus.UNSUPPORTED
    assert answer.sources == ()
    assert generator.prompts == []


def test_repeated_questions_reuse_prepared_index(
    support_corpus: Path,
) -> None:
    embedder = FakeTextEmbedder()
    service = prepare_rag_service(
        embedder,
        FakeAnswerGenerator(),
        top_k=1,
        minimum_similarity=0.75,
        corpus_directory=support_corpus,
    )

    service.answer_question("When should scheduled service occur?")
    service.answer_question("When should scheduled service occur?")

    assert len(embedder.calls) == 3
    assert len(embedder.calls[0]) == 2
    assert embedder.calls[1:] == [
        ("When should scheduled service occur?",),
        ("When should scheduled service occur?",),
    ]


def test_existing_components_validate_service_configuration(
    support_corpus: Path,
) -> None:
    service = prepare_rag_service(
        FakeTextEmbedder(),
        FakeAnswerGenerator(),
        top_k=0,
        minimum_similarity=0.75,
        corpus_directory=support_corpus,
    )

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        service.answer_question("When should scheduled service occur?")


def test_prepared_service_is_immutable(support_corpus: Path) -> None:
    service = prepare_rag_service(
        FakeTextEmbedder(),
        FakeAnswerGenerator(),
        top_k=1,
        minimum_similarity=0.75,
        corpus_directory=support_corpus,
    )

    with pytest.raises(FrozenInstanceError):
        service.top_k = 2  # type: ignore[misc]
