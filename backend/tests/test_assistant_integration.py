"""Cross-route integration and edge-case tests for the unified assistant."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.database import get_db
from app.escalation import EscalationReason, HandoffStatus, HumanHandoffResult
from app.grounded_answers import AnswerSource, GroundedAnswer, UNSUPPORTED_ANSWER
from app.main import (
    app,
    get_evaluation_date,
    get_orchestration_escalation_service,
    get_orchestration_maintenance_service,
    get_orchestration_predictive_service,
    get_orchestration_rag_service,
)
from app.maintenance import MaintenanceDueResult, MaintenanceStatus
from app.predictive_maintenance_comparison import (
    MaintenancePredictionComparison,
    MaintenanceSignalRelationship,
)
from app.predictive_maintenance_prediction import (
    ExperimentalMaintenancePrediction,
    PredictiveMaintenanceFeatureInput,
)
from app.retrieval_confidence import RetrievalSupportStatus


class TrackingMaintenanceService:
    def __init__(self) -> None:
        self.calls: list[tuple[Session, int, date]] = []

    def __call__(
        self,
        session: Session,
        vehicle_id: int,
        evaluation_date: date,
    ) -> MaintenanceDueResult:
        self.calls.append((session, vehicle_id, evaluation_date))
        return MaintenanceDueResult(
            status=MaintenanceStatus.OVERDUE,
            kilometres_travelled_since_last_service=12_000.0,
            kilometres_remaining=-2_000.0,
            months_remaining=-1.0,
            reasons=("Distance caused the authoritative status.",),
        )


class TrackingRagService:
    def __init__(self) -> None:
        self.questions: list[str] = []
        self.error: Exception | None = None
        self.result = GroundedAnswer(
            answer="Use the documented tire-pressure guidance.",
            retrieval_status=RetrievalSupportStatus.SUPPORTED,
            sources=(
                AnswerSource(
                    source_id="tire-care.md",
                    document_title="Tire Care",
                    section_title="Tire Pressure",
                    chunk_id="tire-care.md::chunk-001",
                ),
            ),
        )

    def answer_question(self, question: str) -> GroundedAnswer:
        self.questions.append(question)
        if self.error is not None:
            raise self.error
        return self.result


class TrackingEscalationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, EscalationReason]] = []

    def __call__(
        self,
        user_request: str,
        reason: EscalationReason,
    ) -> HumanHandoffResult:
        self.calls.append((user_request, reason))
        return HumanHandoffResult(
            ticket_id="handoff-integration-001",
            reason=reason,
            request_summary=user_request,
            status=HandoffStatus.CREATED,
        )


class TrackingPredictiveService:
    def __init__(self) -> None:
        self.inputs: list[PredictiveMaintenanceFeatureInput] = []

    def compare(
        self,
        feature_input: PredictiveMaintenanceFeatureInput,
    ) -> MaintenancePredictionComparison:
        self.inputs.append(feature_input)
        return MaintenancePredictionComparison(
            deterministic_result=MaintenanceDueResult(
                status=MaintenanceStatus.NOT_DUE,
                kilometres_travelled_since_last_service=2_000.0,
                kilometres_remaining=8_000.0,
                months_remaining=9.0,
                reasons=("The experimental comparison kept this result.",),
            ),
            experimental_result=ExperimentalMaintenancePrediction(
                maintenance_needed_within_90_days_prediction=1,
                positive_class_probability=0.61,
                threshold=0.19,
                experimental=True,
                artifact_schema_version=1,
            ),
            deterministic_binary_signal=0,
            experimental_ml_binary_signal=1,
            relationship=MaintenanceSignalRelationship.ML_ONLY_POSITIVE,
        )


@dataclass
class IntegrationServices:
    session: Session
    maintenance: TrackingMaintenanceService
    rag: TrackingRagService
    escalation: TrackingEscalationService
    predictive: TrackingPredictiveService

    def call_counts(self) -> tuple[int, int, int, int]:
        return (
            len(self.maintenance.calls),
            len(self.rag.questions),
            len(self.escalation.calls),
            len(self.predictive.inputs),
        )


def predictive_payload() -> dict[str, float]:
    return {
        "vehicle_age_years": 6.0,
        "current_odometer_km": 72_000.0,
        "distance_since_last_scheduled_service_km": 7_500.0,
        "months_since_last_scheduled_service": 8.0,
        "service_interval_km": 10_000.0,
        "service_interval_months": 12.0,
        "average_monthly_driving_km": 1_100.0,
        "usage_severity_score": 0.65,
    }


@pytest.fixture
def integration_client() -> Iterator[tuple[TestClient, IntegrationServices]]:
    services = IntegrationServices(
        session=MagicMock(spec=Session),
        maintenance=TrackingMaintenanceService(),
        rag=TrackingRagService(),
        escalation=TrackingEscalationService(),
        predictive=TrackingPredictiveService(),
    )

    def override_db() -> Iterator[Session]:
        yield services.session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_evaluation_date] = lambda: date(2026, 8, 18)
    app.dependency_overrides[
        get_orchestration_maintenance_service
    ] = lambda: services.maintenance
    app.dependency_overrides[get_orchestration_rag_service] = lambda: services.rag
    app.dependency_overrides[
        get_orchestration_escalation_service
    ] = lambda: services.escalation
    app.dependency_overrides[
        get_orchestration_predictive_service
    ] = lambda: services.predictive
    try:
        with TestClient(app) as client:
            yield client, services
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "message",
    [
        "Is my vehicle due for service, and what does the owner's manual say?",
        (
            "Compare my maintenance status with the experimental ML model and "
            "tell me what the owner's manual says."
        ),
    ],
)
def test_conflicting_capabilities_require_clarification_without_tool_calls(
    integration_client: tuple[TestClient, IntegrationServices],
    message: str,
) -> None:
    client, services = integration_client

    response = client.post(
        "/assistant/query",
        json={
            "message": message,
            "vehicle_id": 42,
            "predictive_maintenance_input": predictive_payload(),
        },
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "clarification_required"
    assert response.json()["invoked_capability"] is None
    assert services.call_counts() == (0, 0, 0, 0)


@pytest.mark.parametrize(
    "message",
    [
        "Connect me to a human agent about whether my vehicle is due for service.",
        "I want to speak to a person about the owner's manual.",
        "My vehicle is unsafe to drive; what does the warning light mean?",
    ],
)
def test_handoff_precedence_executes_only_escalation(
    integration_client: tuple[TestClient, IntegrationServices],
    message: str,
) -> None:
    client, services = integration_client

    response = client.post(
        "/assistant/query",
        json={
            "message": message,
            "vehicle_id": 42,
            "predictive_maintenance_input": predictive_payload(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "executed"
    assert body["invoked_capability"] == "human_handoff"
    assert body["escalation_result"] == {
        "ticket_id": "handoff-integration-001",
        "reason": "routed_human_handoff",
        "request_summary": message,
        "status": "created",
    }
    assert services.call_counts() == (0, 0, 1, 0)


def test_predictive_wording_without_explicit_ml_intent_invokes_nothing(
    integration_client: tuple[TestClient, IntegrationServices],
) -> None:
    client, services = integration_client

    response = client.post(
        "/assistant/query",
        json={
            "message": "Can you predict my vehicle maintenance?",
            "predictive_maintenance_input": predictive_payload(),
        },
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "clarification_required"
    assert services.call_counts() == (0, 0, 0, 0)


@pytest.mark.parametrize(
    ("payload", "outcome", "missing_context"),
    [
        (
            {"message": "Is my vehicle due for service?"},
            "context_required",
            ["vehicle_id"],
        ),
        (
            {"message": "Give me the experimental maintenance prediction."},
            "context_required",
            ["predictive_maintenance_input"],
        ),
        (
            {"message": "Give me a pasta recipe."},
            "unsupported",
            [],
        ),
        (
            {"message": "I need help with my car."},
            "clarification_required",
            [],
        ),
    ],
)
def test_nonexecuted_outcomes_never_invoke_a_service(
    integration_client: tuple[TestClient, IntegrationServices],
    payload: dict[str, object],
    outcome: str,
    missing_context: list[str],
) -> None:
    client, services = integration_client

    response = client.post("/assistant/query", json=payload)

    assert response.status_code == 200
    assert response.json()["outcome"] == outcome
    assert response.json()["missing_context"] == missing_context
    assert services.call_counts() == (0, 0, 0, 0)


def test_support_requires_no_irrelevant_route_context_and_invokes_only_rag(
    integration_client: tuple[TestClient, IntegrationServices],
) -> None:
    client, services = integration_client

    response = client.post(
        "/assistant/query",
        json={"message": "What does the tire pressure warning light mean?"},
    )

    assert response.status_code == 200
    assert response.json()["support_result"] == {
        "answer": "Use the documented tire-pressure guidance.",
        "retrieval_status": "supported",
        "sources": [
            {
                "source_id": "tire-care.md",
                "document_title": "Tire Care",
                "section_title": "Tire Pressure",
                "chunk_id": "tire-care.md::chunk-001",
            }
        ],
    }
    assert services.call_counts() == (0, 1, 0, 0)


def test_unsupported_rag_fallback_does_not_trigger_another_capability(
    integration_client: tuple[TestClient, IntegrationServices],
) -> None:
    client, services = integration_client
    services.rag.result = GroundedAnswer(
        answer=UNSUPPORTED_ANSWER,
        retrieval_status=RetrievalSupportStatus.UNSUPPORTED,
        sources=(),
    )

    response = client.post(
        "/assistant/query",
        json={"message": "What does the tire pressure warning light mean?"},
    )

    assert response.status_code == 200
    assert response.json()["support_result"] == {
        "answer": UNSUPPORTED_ANSWER,
        "retrieval_status": "unsupported",
        "sources": [],
    }
    assert services.call_counts() == (0, 1, 0, 0)


def test_ordinary_maintenance_ignores_supplied_experimental_context(
    integration_client: tuple[TestClient, IntegrationServices],
) -> None:
    client, services = integration_client

    response = client.post(
        "/assistant/query",
        json={
            "message": "Check my maintenance status.",
            "vehicle_id": 42,
            "predictive_maintenance_input": predictive_payload(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["maintenance_result"]["status"] == "overdue"
    assert body["experimental_comparison_result"] is None
    assert services.call_counts() == (1, 0, 0, 0)


def test_experimental_request_requires_no_stored_vehicle_context_or_tools(
    integration_client: tuple[TestClient, IntegrationServices],
) -> None:
    client, services = integration_client

    response = client.post(
        "/assistant/query",
        json={
            "message": "Give me the experimental maintenance prediction.",
            "predictive_maintenance_input": predictive_payload(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["maintenance_result"] is None
    assert body["experimental_comparison_result"]["deterministic"]["status"] == (
        "not_due"
    )
    assert body["experimental_comparison_result"]["experimental_ml"] == {
        "maintenance_needed_within_90_days_prediction": 1,
        "positive_class_probability": 0.61,
        "threshold": 0.19,
        "experimental": True,
        "artifact_schema_version": 1,
    }
    assert body["experimental_comparison_result"]["comparison"] == {
        "deterministic_binary_signal": 0,
        "experimental_ml_binary_signal": 1,
        "relationship": "ml_only_positive",
    }
    response_text = json.dumps(body).casefold()
    assert "final_status" not in response_text
    assert "combined_status" not in response_text
    assert "recommended_status" not in response_text
    assert services.call_counts() == (0, 0, 0, 1)


def test_malformed_request_is_distinct_from_missing_context(
    integration_client: tuple[TestClient, IntegrationServices],
) -> None:
    client, services = integration_client

    malformed = client.post("/assistant/query", json={"message": "   "})
    missing_context = client.post(
        "/assistant/query",
        json={"message": "Is my vehicle due for service?"},
    )

    assert malformed.status_code == 422
    assert missing_context.status_code == 200
    assert missing_context.json()["outcome"] == "context_required"
    assert services.call_counts() == (0, 0, 0, 0)


def test_unhandled_programming_error_is_not_returned_as_success(
    integration_client: tuple[TestClient, IntegrationServices],
) -> None:
    _, services = integration_client
    services.rag.error = RuntimeError("unexpected implementation defect")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/assistant/query",
            json={"message": "What does the tire pressure warning light mean?"},
        )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert services.call_counts() == (0, 1, 0, 0)
