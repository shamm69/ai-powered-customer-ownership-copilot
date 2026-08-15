"""Tests for loading the controlled automotive support corpus."""

from pathlib import Path

import pytest

from app.support_documents import SupportDocument, load_support_documents


def test_default_corpus_loads_expected_documents() -> None:
    documents = load_support_documents()

    assert [document.source_id for document in documents] == [
        "maintenance-basics.md",
        "roadside-support.md",
        "warning-lights.md",
    ]
    assert [document.title for document in documents] == [
        "Scheduled Maintenance Basics",
        "Roadside Support Guidance",
        "Dashboard Warning Lights",
    ]
    assert all(
        document.content.startswith(f"# {document.title}")
        for document in documents
    )


def test_default_corpus_contains_distinct_support_topics() -> None:
    documents = load_support_documents()
    content_by_source = {
        document.source_id: document.content.lower() for document in documents
    }

    assert "distance and time intervals" in content_by_source["maintenance-basics.md"]
    assert "roadside assistance" in content_by_source["roadside-support.md"]
    assert "red warning light" in content_by_source["warning-lights.md"]


def test_loader_uses_markdown_files_and_stable_filename_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "second.md").write_text("# Second\n\nSecond body.", encoding="utf-8")
    (tmp_path / "first.md").write_text("# First\n\nFirst body.", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("Not corpus content.", encoding="utf-8")

    documents = load_support_documents(tmp_path)

    assert documents == (
        SupportDocument(
            source_id="first.md",
            title="First",
            content="# First\n\nFirst body.",
        ),
        SupportDocument(
            source_id="second.md",
            title="Second",
            content="# Second\n\nSecond body.",
        ),
    )


@pytest.mark.parametrize("content", ["", "Document without a Markdown title."])
def test_loader_rejects_invalid_controlled_documents(
    tmp_path: Path,
    content: str,
) -> None:
    (tmp_path / "invalid.md").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        load_support_documents(tmp_path)
