"""Shared test isolation for application startup side effects."""

from collections.abc import Iterator

import pytest
from pytest import MonkeyPatch

from app.runtime_bootstrap import RuntimeBootstrapResult


@pytest.fixture(autouse=True)
def isolate_application_runtime_startup(
    monkeypatch: MonkeyPatch,
) -> Iterator[None]:
    """Keep ordinary API tests away from developer database/artifact paths."""
    from app import main as main_module

    monkeypatch.setattr(
        main_module,
        "initialize_runtime",
        lambda: RuntimeBootstrapResult(
            database_seeded=False,
            predictive_artifact_created=False,
        ),
    )
    yield
