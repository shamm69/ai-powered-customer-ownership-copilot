"""Tests for the FastAPI application foundation."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.gemini_answer_generator import (
    GeminiConfigurationError,
    GeminiGenerationError,
)
from app.grounded_answers import AnswerSource, GroundedAnswer, UNSUPPORTED_ANSWER
from app.main import app, build_rag_service, get_evaluation_date, get_rag_service
from app.maintenance import MaintenanceDueResult, MaintenanceStatus
from app.models import Customer, ServiceRecord, Vehicle
from app.retrieval_confidence import RetrievalSupportStatus

client = TestClient(app)


class FakeRagService:
    def __init__(
        self,
        answer: GroundedAnswer | None = None,
        error: Exception | None = None,
    ) -> None:
        self.answer = answer
        self.error = error
        self.questions: list[str] = []

    def answer_question(self, question: str) -> GroundedAnswer:
        self.questions.append(question)
        if self.error is not None:
            raise self.error
        if self.answer is None:
            raise AssertionError("Fake RAG service requires an answer")
        return self.answer


@pytest.fixture
def support_api_client() -> Iterator[tuple[TestClient, FakeRagService]]:
    fake_service = FakeRagService(
        GroundedAnswer(
            answer="Follow both distance and time service intervals.",
            retrieval_status=RetrievalSupportStatus.SUPPORTED,
            sources=(
                AnswerSource(
                    source_id="maintenance-basics.md",
                    document_title="Scheduled Maintenance Basics",
                    section_title="Scheduled Maintenance Basics",
                    chunk_id="maintenance-basics.md::chunk-001",
                ),
            ),
        )
    )
    app.dependency_overrides[get_rag_service] = lambda: fake_service
    try:
        with TestClient(app) as test_client:
            yield test_client, fake_service
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def stored_data_client() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    """Provide an API client backed by an isolated in-memory database."""
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    test_session_factory = sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )

    def override_get_db() -> Iterator[Session]:
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_evaluation_date] = lambda: date(2026, 8, 11)
    try:
        with TestClient(app) as test_client:
            yield test_client, test_session_factory
    finally:
        app.dependency_overrides.clear()


def add_stored_vehicle(
    session_factory: sessionmaker[Session],
    *,
    with_scheduled_service: bool,
) -> int:
    """Persist a synthetic vehicle for an API test and return its ID."""
    with session_factory() as session:
        vehicle = Vehicle(
            customer=Customer(name="Taylor Morgan"),
            manufacturer="Aster Motors",
            model="Comet",
            model_year=2023,
            current_odometer_km=18_000,
            service_interval_km=10_000,
            service_interval_months=12,
        )
        if with_scheduled_service:
            vehicle.service_records.append(
                ServiceRecord(
                    service_date=date(2026, 1, 15),
                    odometer_km=10_000,
                    service_type="scheduled",
                )
            )
        session.add(vehicle)
        session.commit()
        return vehicle.id


def maintenance_payload(**overrides: float) -> dict[str, float]:
    payload = {
        "current_odometer_km": 14_000,
        "last_service_odometer_km": 10_000,
        "months_since_last_service": 4,
        "service_interval_km": 10_000,
        "service_interval_months": 12,
        "due_soon_threshold_percent": 80,
    }
    payload.update(overrides)
    return payload


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_support_query_returns_supported_answer_and_sources(
    support_api_client: tuple[TestClient, FakeRagService],
) -> None:
    test_client, fake_service = support_api_client

    response = test_client.post(
        "/support/query",
        json={"question": "  When should service be performed?  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Follow both distance and time service intervals.",
        "retrieval_status": "supported",
        "sources": [
            {
                "source_id": "maintenance-basics.md",
                "document_title": "Scheduled Maintenance Basics",
                "section_title": "Scheduled Maintenance Basics",
                "chunk_id": "maintenance-basics.md::chunk-001",
            }
        ],
    }
    assert fake_service.questions == ["When should service be performed?"]


def test_support_query_returns_unsupported_fallback_without_sources(
    support_api_client: tuple[TestClient, FakeRagService],
) -> None:
    test_client, fake_service = support_api_client
    fake_service.answer = GroundedAnswer(
        answer=UNSUPPORTED_ANSWER,
        retrieval_status=RetrievalSupportStatus.UNSUPPORTED,
        sources=(),
    )

    response = test_client.post(
        "/support/query",
        json={"question": "What unrelated information is available?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": UNSUPPORTED_ANSWER,
        "retrieval_status": "unsupported",
        "sources": [],
    }


@pytest.mark.parametrize(
    "payload",
    [{}, {"question": ""}, {"question": "   "}, {"question": 42}],
)
def test_support_query_rejects_invalid_request_input(
    support_api_client: tuple[TestClient, FakeRagService],
    payload: dict[str, object],
) -> None:
    test_client, fake_service = support_api_client

    response = test_client.post("/support/query", json=payload)

    assert response.status_code == 422
    assert fake_service.questions == []


def test_support_query_translates_provider_generation_failure(
    support_api_client: tuple[TestClient, FakeRagService],
) -> None:
    test_client, fake_service = support_api_client
    fake_service.error = GeminiGenerationError("provider detail")

    response = test_client.post(
        "/support/query",
        json={"question": "When should service be performed?"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Support answer provider could not generate a response"
    }


def test_support_query_translates_internal_service_failure(
    support_api_client: tuple[TestClient, FakeRagService],
) -> None:
    test_client, fake_service = support_api_client
    fake_service.error = ValueError("internal detail")

    response = test_client.post(
        "/support/query",
        json={"question": "When should service be performed?"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Support query could not be completed"}


def test_support_query_translates_missing_runtime_configuration() -> None:
    build_rag_service.cache_clear()
    try:
        with patch(
            "app.main.build_rag_service",
            side_effect=GeminiConfigurationError("missing key"),
        ):
            response = client.post(
                "/support/query",
                json={"question": "When should service be performed?"},
            )
    finally:
        build_rag_service.cache_clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Support answer service is not configured"
    }


def test_support_query_translates_preparation_failure() -> None:
    build_rag_service.cache_clear()
    try:
        with patch(
            "app.main.build_rag_service",
            side_effect=RuntimeError("preparation detail"),
        ):
            response = client.post(
                "/support/query",
                json={"question": "When should service be performed?"},
            )
    finally:
        build_rag_service.cache_clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Support answer service could not be prepared"
    }


def test_openapi_schema_includes_typed_support_endpoint() -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/support/query"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SupportQueryRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/SupportQueryResponse"}


def test_evaluate_maintenance_not_due_response() -> None:
    response = client.post("/maintenance/evaluate", json=maintenance_payload())

    assert response.status_code == 200
    assert response.json() == {
        "status": "not_due",
        "kilometres_travelled_since_last_service": 4_000,
        "kilometres_remaining": 6_000,
        "months_remaining": 8,
        "reasons": [
            "Neither distance nor time caused a due status: both remain below the "
            "due-soon threshold."
        ],
    }


def test_evaluate_maintenance_due_soon() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(current_odometer_km=18_000),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "due_soon"


def test_evaluate_maintenance_overdue() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(months_since_last_service=13),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "overdue"


def test_evaluate_maintenance_rejects_negative_input() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(months_since_last_service=-1),
    )

    assert response.status_code == 422


def test_evaluate_maintenance_rejects_reversed_odometers() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(
            current_odometer_km=9_000,
            last_service_odometer_km=10_000,
        ),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "current_odometer_km must not be lower than last_service_odometer_km"
        )
    }


def test_evaluate_maintenance_rejects_invalid_service_interval() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(service_interval_km=0),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("threshold", [0, 100])
def test_evaluate_maintenance_rejects_invalid_threshold(threshold: float) -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(due_soon_threshold_percent=threshold),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "non_finite_value",
    [float("nan"), float("inf"), -float("inf")],
)
def test_evaluate_maintenance_rejects_non_finite_values(
    non_finite_value: float,
) -> None:
    payload = maintenance_payload(current_odometer_km=non_finite_value)

    response = client.post(
        "/maintenance/evaluate",
        content=json.dumps(payload),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422


def test_stored_vehicle_maintenance_returns_typed_response(
    stored_data_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = stored_data_client
    vehicle_id = add_stored_vehicle(
        session_factory,
        with_scheduled_service=True,
    )

    response = test_client.get(f"/vehicles/{vehicle_id}/maintenance")

    assert response.status_code == 200
    assert response.json() == {
        "status": "due_soon",
        "kilometres_travelled_since_last_service": 8_000,
        "kilometres_remaining": 2_000,
        "months_remaining": 6,
        "reasons": [
            "Distance caused due_soon status: the distance due-soon threshold "
            "has been reached or exceeded."
        ],
    }


def test_stored_vehicle_maintenance_returns_404_for_missing_vehicle(
    stored_data_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = stored_data_client

    response = test_client.get("/vehicles/999/maintenance")

    assert response.status_code == 404
    assert response.json() == {"detail": "Vehicle not found"}


def test_stored_vehicle_maintenance_returns_422_without_scheduled_service(
    stored_data_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = stored_data_client
    vehicle_id = add_stored_vehicle(
        session_factory,
        with_scheduled_service=False,
    )

    response = test_client.get(f"/vehicles/{vehicle_id}/maintenance")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Vehicle has no scheduled service record"
    }


def test_stored_vehicle_endpoint_delegates_to_application_service(
    stored_data_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = stored_data_client
    service_result = MaintenanceDueResult(
        status=MaintenanceStatus.NOT_DUE,
        kilometres_travelled_since_last_service=1_000,
        kilometres_remaining=9_000,
        months_remaining=10,
        reasons=("Test result",),
    )

    with patch(
        "app.main.evaluate_vehicle_maintenance",
        return_value=service_result,
    ) as evaluator:
        response = test_client.get("/vehicles/42/maintenance")

    assert response.status_code == 200
    evaluator.assert_called_once()
    assert evaluator.call_args.kwargs["vehicle_id"] == 42
    assert evaluator.call_args.kwargs["evaluation_date"] == date(2026, 8, 11)
    assert isinstance(evaluator.call_args.kwargs["session"], Session)
