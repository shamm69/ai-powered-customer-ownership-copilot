"""Tests for local embedding and indexed document chunks."""

import sys
from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from types import ModuleType

import pytest

from app.document_chunking import DocumentChunk
from app.document_embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    IndexedDocumentChunk,
    SentenceTransformerEmbedder,
    index_document_chunks,
)


def make_chunk(chunk_id: str, content: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        source_id="support.md",
        document_title="Support Guide",
        section_title="Maintenance",
        content=content,
    )


class FakeEmbedder:
    def __init__(self, embeddings: Sequence[Sequence[float]]) -> None:
        self.embeddings = embeddings
        self.received_texts: tuple[str, ...] | None = None

    def embed_texts(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        self.received_texts = tuple(texts)
        return self.embeddings


def test_indexing_preserves_chunk_order_metadata_and_vectors() -> None:
    chunks = (
        make_chunk("support.md::chunk-001", "First support paragraph."),
        make_chunk("support.md::chunk-002", "Second support paragraph."),
    )
    embedder = FakeEmbedder(((0.1, 0.2), (0.3, 0.4)))

    indexed_chunks = index_document_chunks(chunks, embedder)

    assert embedder.received_texts == (
        "First support paragraph.",
        "Second support paragraph.",
    )
    assert indexed_chunks == (
        IndexedDocumentChunk(chunk=chunks[0], embedding=(0.1, 0.2)),
        IndexedDocumentChunk(chunk=chunks[1], embedding=(0.3, 0.4)),
    )


def test_indexed_chunk_is_immutable() -> None:
    indexed_chunk = IndexedDocumentChunk(
        chunk=make_chunk("support.md::chunk-001", "Support paragraph."),
        embedding=(0.1, 0.2),
    )

    with pytest.raises(FrozenInstanceError):
        indexed_chunk.embedding = (0.3, 0.4)  # type: ignore[misc]


def test_empty_chunk_collection_does_not_call_embedder() -> None:
    embedder = FakeEmbedder(())

    assert index_document_chunks((), embedder) == ()
    assert embedder.received_texts is None


@pytest.mark.parametrize(
    ("embeddings", "message"),
    [
        ((), "one vector for each document chunk"),
        (((),), "must not be empty"),
        (((0.1, float("nan")),), "only finite values"),
        (((0.1, float("inf")),), "only finite values"),
        ((("invalid", 0.2),), "numeric values"),
    ],
)
def test_indexing_rejects_invalid_embedding_results(
    embeddings: Sequence[Sequence[float]],
    message: str,
) -> None:
    chunk = make_chunk("support.md::chunk-001", "Support paragraph.")

    with pytest.raises(ValueError, match=message):
        index_document_chunks((chunk,), FakeEmbedder(embeddings))


def test_indexing_rejects_inconsistent_embedding_dimensions() -> None:
    chunks = (
        make_chunk("support.md::chunk-001", "First support paragraph."),
        make_chunk("support.md::chunk-002", "Second support paragraph."),
    )

    with pytest.raises(ValueError, match="consistent dimensions"):
        index_document_chunks(chunks, FakeEmbedder(((0.1, 0.2), (0.3,))))


def test_sentence_transformer_adapter_uses_local_cpu_model(monkeypatch: pytest.MonkeyPatch) -> None:
    created_models: list[tuple[str, str]] = []
    encode_calls: list[tuple[list[str], bool, bool]] = []

    class FakeSentenceTransformer:
        def __init__(self, model_name: str, device: str) -> None:
            created_models.append((model_name, device))

        def encode(
            self,
            texts: list[str],
            *,
            convert_to_numpy: bool,
            show_progress_bar: bool,
        ) -> tuple[tuple[float, ...], ...]:
            encode_calls.append((texts, convert_to_numpy, show_progress_bar))
            return ((0.1, 0.2),)

    fake_module = ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    embedder = SentenceTransformerEmbedder()

    assert embedder.embed_texts(("Support text.",)) == ((0.1, 0.2),)
    assert created_models == [(DEFAULT_EMBEDDING_MODEL, "cpu")]
    assert encode_calls == [(["Support text."], True, False)]
