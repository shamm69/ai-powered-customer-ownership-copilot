"""Deterministic Markdown-aware chunking for support documents."""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.support_documents import SupportDocument

MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")


@dataclass(frozen=True)
class DocumentChunk:
    """A retrieval-ready paragraph with stable source metadata."""

    chunk_id: str
    source_id: str
    document_title: str
    section_title: str
    content: str


def chunk_support_document(document: SupportDocument) -> tuple[DocumentChunk, ...]:
    """Split one Markdown document into ordered, nonempty paragraph chunks."""
    section_title = document.title
    paragraph_lines: list[str] = []
    paragraphs: list[tuple[str, str]] = []

    def finish_paragraph() -> None:
        if not paragraph_lines:
            return
        content = "\n".join(paragraph_lines).strip()
        paragraph_lines.clear()
        if content:
            paragraphs.append((section_title, content))

    for line in document.content.splitlines():
        heading_match = MARKDOWN_HEADING.match(line.strip())
        if heading_match:
            finish_paragraph()
            section_title = heading_match.group(1).strip()
        elif not line.strip():
            finish_paragraph()
        else:
            paragraph_lines.append(line.rstrip())
    finish_paragraph()

    return tuple(
        DocumentChunk(
            chunk_id=f"{document.source_id}::chunk-{index:03d}",
            source_id=document.source_id,
            document_title=document.title,
            section_title=paragraph_section,
            content=content,
        )
        for index, (paragraph_section, content) in enumerate(paragraphs, start=1)
    )


def chunk_support_documents(
    documents: Iterable[SupportDocument],
) -> tuple[DocumentChunk, ...]:
    """Chunk documents while preserving their input order."""
    return tuple(
        chunk
        for document in documents
        for chunk in chunk_support_document(document)
    )
