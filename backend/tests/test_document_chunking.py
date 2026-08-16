"""Tests for deterministic support-document chunking."""

from app.document_chunking import (
    DocumentChunk,
    chunk_support_document,
    chunk_support_documents,
)
from app.support_documents import SupportDocument, load_support_documents


def test_default_corpus_produces_stable_ordered_chunks() -> None:
    chunks = chunk_support_documents(load_support_documents())

    assert len(chunks) == 9
    assert [chunk.chunk_id for chunk in chunks] == [
        "maintenance-basics.md::chunk-001",
        "maintenance-basics.md::chunk-002",
        "maintenance-basics.md::chunk-003",
        "roadside-support.md::chunk-001",
        "roadside-support.md::chunk-002",
        "roadside-support.md::chunk-003",
        "warning-lights.md::chunk-001",
        "warning-lights.md::chunk-002",
        "warning-lights.md::chunk-003",
    ]


def test_chunks_preserve_document_and_section_metadata() -> None:
    chunks = chunk_support_documents(load_support_documents())
    first_chunk = chunks[0]

    assert first_chunk.source_id == "maintenance-basics.md"
    assert first_chunk.document_title == "Scheduled Maintenance Basics"
    assert first_chunk.section_title == "Scheduled Maintenance Basics"
    assert "distance and time intervals" in first_chunk.content


def test_markdown_headings_define_section_metadata() -> None:
    document = SupportDocument(
        source_id="vehicle-guide.md",
        title="Vehicle Guide",
        content=(
            "# Vehicle Guide\n\n"
            "General guidance.\n\n"
            "## Tires\n\n"
            "Check tire pressure.\nKeep the valve caps fitted.\n\n"
            "Replace damaged tires."
        ),
    )

    chunks = chunk_support_document(document)

    assert chunks == (
        DocumentChunk(
            chunk_id="vehicle-guide.md::chunk-001",
            source_id="vehicle-guide.md",
            document_title="Vehicle Guide",
            section_title="Vehicle Guide",
            content="General guidance.",
        ),
        DocumentChunk(
            chunk_id="vehicle-guide.md::chunk-002",
            source_id="vehicle-guide.md",
            document_title="Vehicle Guide",
            section_title="Tires",
            content="Check tire pressure.\nKeep the valve caps fitted.",
        ),
        DocumentChunk(
            chunk_id="vehicle-guide.md::chunk-003",
            source_id="vehicle-guide.md",
            document_title="Vehicle Guide",
            section_title="Tires",
            content="Replace damaged tires.",
        ),
    )


def test_chunking_is_deterministic() -> None:
    documents = load_support_documents()

    assert chunk_support_documents(documents) == chunk_support_documents(documents)


def test_chunking_emits_no_empty_chunks_or_loses_body_paragraphs() -> None:
    documents = load_support_documents()
    chunks = chunk_support_documents(documents)

    assert all(chunk.content.strip() for chunk in chunks)
    assert sum(len(document.content.split("\n\n")) - 1 for document in documents) == len(
        chunks
    )
