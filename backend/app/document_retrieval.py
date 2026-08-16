"""Deterministic in-memory semantic retrieval for support chunks."""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.document_embeddings import (
    IndexedDocumentChunk,
    TextEmbedder,
    validate_embedding_vector,
)


@dataclass(frozen=True)
class RetrievalResult:
    """An indexed chunk paired with its query similarity score."""

    indexed_chunk: IndexedDocumentChunk
    similarity_score: float


def retrieve_similar_chunks(
    query: str,
    indexed_chunks: Iterable[IndexedDocumentChunk],
    embedder: TextEmbedder,
    top_k: int,
) -> tuple[RetrievalResult, ...]:
    """Return the top-k indexed chunks ranked by cosine similarity."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Query must not be empty or blank")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer")

    ordered_chunks = tuple(indexed_chunks)
    if not ordered_chunks:
        return ()

    query_embeddings = embedder.embed_texts((normalized_query,))
    if len(query_embeddings) != 1:
        raise ValueError("Embedder must return exactly one query vector")
    query_embedding = validate_embedding_vector(query_embeddings[0])

    scored_chunks = tuple(
        RetrievalResult(
            indexed_chunk=indexed_chunk,
            similarity_score=_cosine_similarity(
                query_embedding,
                indexed_chunk.embedding,
            ),
        )
        for indexed_chunk in ordered_chunks
    )
    ranked_chunks = sorted(
        enumerate(scored_chunks),
        key=lambda item: (-item[1].similarity_score, item[0]),
    )
    return tuple(result for _, result in ranked_chunks[:top_k])


def _cosine_similarity(
    first_vector: Sequence[float],
    second_vector: Sequence[float],
) -> float:
    first = validate_embedding_vector(first_vector)
    second = validate_embedding_vector(second_vector)
    if len(first) != len(second):
        raise ValueError("Query and chunk embeddings must have matching dimensions")

    first_magnitude = math.sqrt(sum(value * value for value in first))
    second_magnitude = math.sqrt(sum(value * value for value in second))
    if first_magnitude == 0.0 or second_magnitude == 0.0:
        raise ValueError("Cosine similarity requires non-zero embedding vectors")

    dot_product = sum(
        first_value * second_value
        for first_value, second_value in zip(first, second, strict=True)
    )
    return dot_product / (first_magnitude * second_magnitude)
