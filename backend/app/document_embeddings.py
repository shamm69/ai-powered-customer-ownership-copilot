"""Local embedding and indexed-chunk foundation for support documents."""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.document_chunking import DocumentChunk

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class TextEmbedder(Protocol):
    """Small boundary for converting ordered text into numeric vectors."""

    def embed_texts(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Return one embedding for each input text, in the same order."""


class SentenceTransformerEmbedder:
    """CPU-only local text embedder backed by Sentence Transformers."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        if not model_name.strip():
            raise ValueError("Embedding model name must not be empty")

        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model: Any = SentenceTransformer(model_name, device="cpu")

    def embed_texts(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """Embed text locally while preserving the supplied order."""
        if not texts:
            return ()

        embeddings = self._model.encode(
            list(texts),
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return tuple(
            tuple(float(value) for value in embedding) for embedding in embeddings
        )


@dataclass(frozen=True)
class IndexedDocumentChunk:
    """An immutable document chunk paired with its embedding vector."""

    chunk: DocumentChunk
    embedding: tuple[float, ...]


def index_document_chunks(
    chunks: Iterable[DocumentChunk],
    embedder: TextEmbedder,
) -> tuple[IndexedDocumentChunk, ...]:
    """Embed ordered chunks and retain their complete original metadata."""
    ordered_chunks = tuple(chunks)
    if not ordered_chunks:
        return ()

    raw_embeddings = embedder.embed_texts(
        tuple(chunk.content for chunk in ordered_chunks)
    )
    if len(raw_embeddings) != len(ordered_chunks):
        raise ValueError("Embedder must return one vector for each document chunk")

    embeddings = tuple(
        _validate_embedding(embedding) for embedding in raw_embeddings
    )
    expected_dimensions = len(embeddings[0])
    if any(len(embedding) != expected_dimensions for embedding in embeddings[1:]):
        raise ValueError("Embedding vectors must have consistent dimensions")

    return tuple(
        IndexedDocumentChunk(chunk=chunk, embedding=embedding)
        for chunk, embedding in zip(ordered_chunks, embeddings, strict=True)
    )


def _validate_embedding(embedding: Sequence[float]) -> tuple[float, ...]:
    try:
        vector = tuple(float(value) for value in embedding)
    except (TypeError, ValueError) as error:
        raise ValueError("Embedding vectors must contain numeric values") from error

    if not vector:
        raise ValueError("Embedding vectors must not be empty")
    if not all(math.isfinite(value) for value in vector):
        raise ValueError("Embedding vectors must contain only finite values")
    return vector
