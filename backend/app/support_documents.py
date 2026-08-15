"""Load the controlled automotive support knowledge corpus."""

from dataclasses import dataclass
from pathlib import Path

DEFAULT_CORPUS_DIRECTORY = Path(__file__).resolve().parent.parent / "knowledge"


@dataclass(frozen=True)
class SupportDocument:
    """A support document with metadata needed for later retrieval."""

    source_id: str
    title: str
    content: str


def load_support_documents(
    corpus_directory: Path = DEFAULT_CORPUS_DIRECTORY,
) -> tuple[SupportDocument, ...]:
    """Load Markdown support documents in deterministic filename order."""
    if not corpus_directory.is_dir():
        raise FileNotFoundError(
            f"Support corpus directory not found: {corpus_directory}"
        )

    documents: list[SupportDocument] = []
    for document_path in sorted(corpus_directory.glob("*.md")):
        content = document_path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"Support document is empty: {document_path.name}")

        first_line = content.splitlines()[0]
        if not first_line.startswith("# "):
            raise ValueError(
                f"Support document must start with a title: {document_path.name}"
            )

        documents.append(
            SupportDocument(
                source_id=document_path.name,
                title=first_line.removeprefix("# ").strip(),
                content=content,
            )
        )

    return tuple(documents)
