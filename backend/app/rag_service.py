"""Application service composing the support-document RAG pipeline."""

from dataclasses import dataclass
from pathlib import Path

from app.document_chunking import chunk_support_documents
from app.document_embeddings import (
    IndexedDocumentChunk,
    TextEmbedder,
    index_document_chunks,
)
from app.document_retrieval import retrieve_similar_chunks
from app.grounded_answers import (
    AnswerGenerator,
    GroundedAnswer,
    generate_grounded_answer,
)
from app.retrieval_confidence import assess_retrieval_support
from app.support_documents import (
    DEFAULT_CORPUS_DIRECTORY,
    load_support_documents,
)


@dataclass(frozen=True)
class RagService:
    """Prepared in-memory support index and its query dependencies."""

    indexed_chunks: tuple[IndexedDocumentChunk, ...]
    embedder: TextEmbedder
    answer_generator: AnswerGenerator
    top_k: int
    minimum_similarity: float

    def answer_question(self, question: str) -> GroundedAnswer:
        """Run retrieval, confidence gating, and grounded generation."""
        retrieval_results = retrieve_similar_chunks(
            question,
            self.indexed_chunks,
            self.embedder,
            top_k=self.top_k,
        )
        support_decision = assess_retrieval_support(
            retrieval_results,
            minimum_similarity=self.minimum_similarity,
        )
        return generate_grounded_answer(
            question,
            support_decision,
            self.answer_generator,
        )


def prepare_rag_service(
    embedder: TextEmbedder,
    answer_generator: AnswerGenerator,
    *,
    top_k: int,
    minimum_similarity: float,
    corpus_directory: Path = DEFAULT_CORPUS_DIRECTORY,
) -> RagService:
    """Load, chunk, and index the controlled corpus once for later queries."""
    documents = load_support_documents(corpus_directory)
    chunks = chunk_support_documents(documents)
    indexed_chunks = index_document_chunks(chunks, embedder)
    return RagService(
        indexed_chunks=indexed_chunks,
        embedder=embedder,
        answer_generator=answer_generator,
        top_k=top_k,
        minimum_similarity=minimum_similarity,
    )
