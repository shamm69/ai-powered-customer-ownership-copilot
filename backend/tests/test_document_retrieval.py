"""Tests for deterministic in-memory semantic retrieval."""

from collections.abc import Sequence
from dataclasses import FrozenInstanceError

import pytest

from app.document_chunking import DocumentChunk
from app.document_embeddings import IndexedDocumentChunk
from app.document_retrieval import RetrievalResult, retrieve_similar_chunks


class FakeEmbedder:
    def __init__(self, embeddings: Sequence[Sequence[float]]) -> None:
        self.embeddings = embeddings
        self.received_texts: tuple[str, ...] | None = None

    def embed_texts(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        self.received_texts = tuple(texts)
        return self.embeddings


def make_indexed_chunk(
    chunk_id: str,
    source_id: str,
    content: str,
    embedding: tuple[float, ...],
) -> IndexedDocumentChunk:
    return IndexedDocumentChunk(
        chunk=DocumentChunk(
            chunk_id=chunk_id,
            source_id=source_id,
            document_title="Support Guide",
            section_title="Support Section",
            content=content,
        ),
        embedding=embedding,
    )


def test_retrieval_ranks_chunks_by_cosine_similarity_and_limits_top_k() -> None:
    maintenance = make_indexed_chunk(
        "maintenance.md::chunk-001",
        "maintenance.md",
        "Maintenance guidance.",
        (1.0, 0.0),
    )
    roadside = make_indexed_chunk(
        "roadside.md::chunk-001",
        "roadside.md",
        "Roadside guidance.",
        (0.0, 1.0),
    )
    mixed = make_indexed_chunk(
        "general.md::chunk-001",
        "general.md",
        "General guidance.",
        (0.8, 0.2),
    )

    results = retrieve_similar_chunks(
        "maintenance interval",
        (roadside, mixed, maintenance),
        FakeEmbedder(((1.0, 0.0),)),
        top_k=2,
    )

    assert [result.indexed_chunk for result in results] == [maintenance, mixed]
    assert results[0].similarity_score == pytest.approx(1.0)
    assert results[1].similarity_score == pytest.approx(0.9701425)


def test_retrieval_preserves_metadata_and_strips_query() -> None:
    indexed_chunk = make_indexed_chunk(
        "warning-lights.md::chunk-001",
        "warning-lights.md",
        "Warning light guidance.",
        (1.0, 0.0),
    )
    embedder = FakeEmbedder(((1.0, 0.0),))

    result = retrieve_similar_chunks(
        "  warning light  ",
        (indexed_chunk,),
        embedder,
        top_k=1,
    )[0]

    assert embedder.received_texts == ("warning light",)
    assert result.indexed_chunk is indexed_chunk
    assert result.indexed_chunk.chunk.source_id == "warning-lights.md"


def test_equal_scores_preserve_original_indexed_chunk_order() -> None:
    first = make_indexed_chunk(
        "support.md::chunk-002", "support.md", "First input.", (1.0, 1.0)
    )
    second = make_indexed_chunk(
        "support.md::chunk-001", "support.md", "Second input.", (1.0, 1.0)
    )

    results = retrieve_similar_chunks(
        "support",
        (first, second),
        FakeEmbedder(((1.0, 0.0),)),
        top_k=2,
    )

    assert [result.indexed_chunk for result in results] == [first, second]


def test_retrieval_result_is_immutable() -> None:
    indexed_chunk = make_indexed_chunk(
        "support.md::chunk-001", "support.md", "Support.", (1.0, 0.0)
    )
    result = RetrievalResult(indexed_chunk=indexed_chunk, similarity_score=1.0)

    with pytest.raises(FrozenInstanceError):
        result.similarity_score = 0.5  # type: ignore[misc]


@pytest.mark.parametrize("query", ["", "   ", "\n\t"])
def test_retrieval_rejects_empty_or_blank_query(query: str) -> None:
    indexed_chunk = make_indexed_chunk(
        "support.md::chunk-001", "support.md", "Support.", (1.0, 0.0)
    )

    with pytest.raises(ValueError, match="Query must not be empty or blank"):
        retrieve_similar_chunks(
            query, (indexed_chunk,), FakeEmbedder(((1.0, 0.0),)), top_k=1
        )


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_retrieval_rejects_invalid_top_k(top_k: object) -> None:
    indexed_chunk = make_indexed_chunk(
        "support.md::chunk-001", "support.md", "Support.", (1.0, 0.0)
    )

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        retrieve_similar_chunks(
            "support",
            (indexed_chunk,),
            FakeEmbedder(((1.0, 0.0),)),
            top_k=top_k,  # type: ignore[arg-type]
        )


def test_empty_index_returns_no_results_without_embedding_query() -> None:
    embedder = FakeEmbedder(((1.0, 0.0),))

    assert retrieve_similar_chunks("support", (), embedder, top_k=3) == ()
    assert embedder.received_texts is None


def test_retrieval_rejects_incompatible_vector_dimensions() -> None:
    indexed_chunk = make_indexed_chunk(
        "support.md::chunk-001", "support.md", "Support.", (1.0, 0.0, 0.0)
    )

    with pytest.raises(ValueError, match="matching dimensions"):
        retrieve_similar_chunks(
            "support",
            (indexed_chunk,),
            FakeEmbedder(((1.0, 0.0),)),
            top_k=1,
        )


@pytest.mark.parametrize(
    "query_embeddings",
    [(), ((0.0, 0.0),), ((float("nan"), 1.0),)],
)
def test_retrieval_rejects_invalid_query_embeddings(
    query_embeddings: Sequence[Sequence[float]],
) -> None:
    indexed_chunk = make_indexed_chunk(
        "support.md::chunk-001", "support.md", "Support.", (1.0, 0.0)
    )

    with pytest.raises(ValueError):
        retrieve_similar_chunks(
            "support",
            (indexed_chunk,),
            FakeEmbedder(query_embeddings),
            top_k=1,
        )


def test_retrieval_rejects_zero_magnitude_chunk_embedding() -> None:
    indexed_chunk = make_indexed_chunk(
        "support.md::chunk-001", "support.md", "Support.", (0.0, 0.0)
    )

    with pytest.raises(ValueError, match="non-zero embedding vectors"):
        retrieve_similar_chunks(
            "support",
            (indexed_chunk,),
            FakeEmbedder(((1.0, 0.0),)),
            top_k=1,
        )
