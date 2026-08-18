"""Focused tests for the unified FastAPI orchestration endpoint."""

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
from app.gemini_answer_generator import GeminiGenerationError
from app.grounded_answers import AnswerSource, GroundedAnswer, UNSUPPORTED_ANSWER
from app.main import (
    app,
    get_evaluation_date,
    get_orchestration_escalation_service,
    get_orchestration_maintenance_service,
    get_orchestration_predictive_service,
    get_orchestration_rag_service,
    get_orchestration_recommendation_service,
)
from app.maintenance import MaintenanceDueResult, MaintenanceStatus
from app.maintenance_service import (
    MaintenanceServiceError,
    ScheduledServiceNotFoundError,
    VehicleNotFoundError,
)
from app.predictive_maintenance_comparison import (
    MaintenancePredictionComparison,
    MaintenanceSignalRelationship,
)
from app.predictive_maintenance_prediction import (
    ExperimentalMaintenancePrediction,
    ExperimentalMaintenancePredictionError,
    PredictiveMaintenanceFeatureInput,
)
from app.retrieval_confidence import RetrievalSupportStatus
from app.service_recommendations import (
    RecommendationContext,
    RecommendationPriority,
    ServiceRecommendation,
    ServiceRecommendationResult,
    ServiceType,
)


class FakeMaintenanceService:
    def __init__(self, result: MaintenanceDueResult) -> None:
        self.result = result
        self.error: Exception | None = None
        self.calls: list[tuple[Session, int, date]] = []

    def __call__(
        self,
        session: Session,
        vehicle_id: int,
        evaluation_date: date,
    ) -> MaintenanceDueResult:
        self.calls.append((session, vehicle_id, evaluation_date))
        if self.error is not None:
            raise self.error
        return self.result


class FakeRagService:
    def __init__(self, result: GroundedAnswer) -> None:
        self.result = result
        self.error: Exception | None = None
        self.questions: list[str] = []

    def answer_question(self, question: str) -> GroundedAnswer:
        self.questions.append(question)
        if self.error is not None:
            raise self.error
        return self.result


class FakeEscalationService:
    def __init__(self, result: HumanHandoffResult) -> None:
        self.result = result
        self.calls: list[tuple[str, EscalationReason]] = []

    def __call__(
        self,
        user_request: str,
        reason: EscalationReason,
    ) -> HumanHandoffResult:
        self.calls.append((user_request, reason))
        return self.result


class FakePredictiveComparisonService:
    def __init__(self, result: MaintenancePredictionComparison) -> None:
        self.result = result
        self.error: Exception | None = None
        self.inputs: list[PredictiveMaintenanceFeatureInput] = []

    def compare(
        self,
        feature_input: PredictiveMaintenanceFeatureInput,
    ) -> MaintenancePredictionComparison:
        self.inputs.append(feature_input)
        if self.error is not None:
            raise self.error
        return self.result


class FakeRecommendationService:
    def __init__(self, result: ServiceRecommendationResult) -> None:
        self.result = result
        self.calls: list[tuple[Session, int, date, RecommendationContext]] = []

    def __call__(
        self,
        session: Session,
        vehicle_id: int,
        evaluation_date: date,
        recommendation_context: RecommendationContext,
    ) -> ServiceRecommendationResult:
        self.calls.append(
            (session, vehicle_id, evaluation_date, recommendation_context)
        )
        return self.result


@dataclass
class AssistantFakes:
    session: Session
    maintenance: FakeMaintenanceService
    rag: FakeRagService
    escalation: FakeEscalationService
    predictive: FakePredictiveComparisonService
    recommendation: FakeRecommendationService


def maintenance_result() -> MaintenanceDueResult:
    return MaintenanceDueResult(
        status=MaintenanceStatus.DUE_SOON,
        kilometres_travelled_since_last_service=8_000.0,
        kilometres_remaining=2_000.0,
        months_remaining=4.0,
        reasons=("Distance caused the deterministic result.",),
    )


def supported_answer() -> GroundedAnswer:
    return GroundedAnswer(
        answer="Check the documented tire pressure guidance.",
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


def handoff_result() -> HumanHandoffResult:
    return HumanHandoffResult(
        ticket_id="handoff-fixed-001",
        reason=EscalationReason.ROUTED_HUMAN_HANDOFF,
        request_summary="I want to speak to a person.",
        status=HandoffStatus.CREATED,
    )


def predictive_result() -> MaintenancePredictionComparison:
    return MaintenancePredictionComparison(
        deterministic_result=maintenance_result(),
        experimental_result=ExperimentalMaintenancePrediction(
            maintenance_needed_within_90_days_prediction=1,
            positive_class_probability=0.64,
            threshold=0.19,
            experimental=True,
            artifact_schema_version=1,
        ),
        deterministic_binary_signal=1,
        experimental_ml_binary_signal=1,
        relationship=MaintenanceSignalRelationship.AGREE_POSITIVE,
    )


def recommendation_result() -> ServiceRecommendationResult:
    return ServiceRecommendationResult(
        maintenance_result=maintenance_result(),
        recommendations=(
            ServiceRecommendation(
                service_type=ServiceType.PRE_TRIP_INSPECTION,
                priority=RecommendationPriority.RECOMMENDED,
                reason="Preventive inspection before the stated long trip.",
                supporting_factors=("Explicit long-trip context.",),
            ),
        ),
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
def assistant_client() -> Iterator[tuple[TestClient, AssistantFakes]]:
    fakes = AssistantFakes(
        session=MagicMock(spec=Session),
        maintenance=FakeMaintenanceService(maintenance_result()),
        rag=FakeRagService(supported_answer()),
        escalation=FakeEscalationService(handoff_result()),
        predictive=FakePredictiveComparisonService(predictive_result()),
        recommendation=FakeRecommendationService(recommendation_result()),
    )

    def override_db() -> Iterator[Session]:
        yield fakes.session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_evaluation_date] = lambda: date(2026, 8, 18)
    app.dependency_overrides[
        get_orchestration_maintenance_service
    ] = lambda: fakes.maintenance
    app.dependency_overrides[get_orchestration_rag_service] = lambda: fakes.rag
    app.dependency_overrides[
        get_orchestration_escalation_service
    ] = lambda: fakes.escalation
    app.dependency_overrides[
        get_orchestration_predictive_service
    ] = lambda: fakes.predictive
    app.dependency_overrides[
        get_orchestration_recommendation_service
    ] = lambda: fakes.recommendation
    try:
        with TestClient(app) as client:
            yield client, fakes
    finally:
        app.dependency_overrides.clear()


def test_unified_maintenance_request_executes_with_vehicle_context(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client

    response = client.post(
        "/assistant/query",
        json={
            "message": "Is my vehicle due for service?",
            "vehicle_id": 42,
            "evaluation_date": "2026-08-20",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "executed"
    assert body["invoked_capability"] == "stored_vehicle_maintenance"
    assert body["maintenance_result"]["status"] == "due_soon"
    assert fakes.maintenance.calls == [
        (fakes.session, 42, date(2026, 8, 20))
    ]


def test_unified_recommendation_request_returns_typed_result(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client

    response = client.post(
        "/assistant/query",
        json={
            "message": "What should I check before a long trip?",
            "vehicle_id": 42,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["invoked_capability"] == "service_recommendation"
    assert body["maintenance_result"] is None
    assert body["recommendation_result"] == {
        "authoritative_maintenance": {
            "status": "due_soon",
            "kilometres_travelled_since_last_service": 8000.0,
            "kilometres_remaining": 2000.0,
            "months_remaining": 4.0,
            "reasons": ["Distance caused the deterministic result."],
        },
        "recommendations": [
            {
                "service_type": "pre_trip_inspection",
                "priority": "recommended",
                "reason": "Preventive inspection before the stated long trip.",
                "supporting_factors": ["Explicit long-trip context."],
            }
        ],
    }
    assert fakes.recommendation.calls == [
        (
            fakes.session,
            42,
            date(2026, 8, 18),
            RecommendationContext.LONG_TRIP,
        )
    ]
    assert fakes.rag.questions == []
    assert fakes.escalation.calls == []
    assert fakes.predictive.inputs == []


def test_missing_vehicle_context_is_a_typed_normal_response(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client

    response = client.post(
        "/assistant/query",
        json={"message": "Is my vehicle due for service?"},
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "context_required"
    assert response.json()["missing_context"] == ["vehicle_id"]
    assert fakes.maintenance.calls == []


def test_support_request_preserves_grounded_answer_and_sources(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client

    response = client.post(
        "/assistant/query",
        json={"message": "What does the tire pressure warning light mean?"},
    )

    assert response.status_code == 200
    support = response.json()["support_result"]
    assert support["retrieval_status"] == "supported"
    assert support["sources"] == [
        {
            "source_id": "tire-care.md",
            "document_title": "Tire Care",
            "section_title": "Tire Pressure",
            "chunk_id": "tire-care.md::chunk-001",
        }
    ]
    assert fakes.rag.questions == [
        "What does the tire pressure warning light mean?"
    ]


def test_low_confidence_support_fallback_remains_unchanged(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client
    fakes.rag.result = GroundedAnswer(
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


def test_handoff_request_executes_mock_escalation(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client

    response = client.post(
        "/assistant/query",
        json={"message": "I want to speak to a person."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["invoked_capability"] == "human_handoff"
    assert body["escalation_result"]["ticket_id"] == "handoff-fixed-001"
    assert fakes.escalation.calls == [
        (
            "I want to speak to a person.",
            EscalationReason.ROUTED_HUMAN_HANDOFF,
        )
    ]


def test_explicit_predictive_request_preserves_separate_comparison(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client
    features = predictive_payload()

    response = client.post(
        "/assistant/query",
        json={
            "message": (
                "Compare my maintenance status with the experimental ML model."
            ),
            "predictive_maintenance_input": features,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["maintenance_result"] is None
    comparison = body["experimental_comparison_result"]
    assert comparison["deterministic"]["status"] == "due_soon"
    assert comparison["experimental_ml"]["experimental"] is True
    assert comparison["experimental_ml"]["threshold"] == 0.19
    assert comparison["comparison"]["relationship"] == "agree_positive"
    assert fakes.predictive.inputs == [
        PredictiveMaintenanceFeatureInput(**features)
    ]
    serialized = json.dumps(body)
    assert "final_status" not in serialized
    assert "combined_status" not in serialized


def test_explicit_predictive_request_without_features_requires_context(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client

    response = client.post(
        "/assistant/query",
        json={"message": "Give me the experimental maintenance prediction."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "context_required"
    assert body["missing_context"] == ["predictive_maintenance_input"]
    assert body["experimental_comparison_result"] is None
    assert fakes.predictive.inputs == []


def test_ordinary_maintenance_never_invokes_experimental_comparison(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client

    response = client.post(
        "/assistant/query",
        json={"message": "Check my maintenance status.", "vehicle_id": 42},
    )

    assert response.status_code == 200
    assert fakes.predictive.inputs == []
    assert response.json()["experimental_comparison_result"] is None


def test_unsupported_request_returns_explicit_outcome(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, _ = assistant_client

    response = client.post(
        "/assistant/query",
        json={"message": "Give me a pasta recipe."},
    )

    assert response.status_code == 200
    assert response.json()["routing_decision"]["intent"] == "unsupported"
    assert response.json()["outcome"] == "unsupported"


def test_ambiguous_request_returns_clarification_outcome(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, _ = assistant_client

    response = client.post(
        "/assistant/query",
        json={
            "message": (
                "Is my vehicle due for service, and what does the owner's "
                "manual say?"
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["routing_decision"]["intent"] == "clarification_required"
    assert body["outcome"] == "clarification_required"


@pytest.mark.parametrize(
    ("service_error", "expected_status", "expected_detail"),
    [
        (VehicleNotFoundError("internal"), 404, "Vehicle not found"),
        (
            ScheduledServiceNotFoundError("internal"),
            422,
            "Vehicle has no scheduled service record",
        ),
        (
            MaintenanceServiceError("internal"),
            422,
            "Maintenance evaluation could not be completed",
        ),
    ],
)
def test_known_maintenance_errors_use_existing_http_translation(
    assistant_client: tuple[TestClient, AssistantFakes],
    service_error: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    client, fakes = assistant_client
    fakes.maintenance.error = service_error

    response = client.post(
        "/assistant/query",
        json={"message": "Check my maintenance status.", "vehicle_id": 42},
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": "   "},
        {"message": "Check my maintenance status.", "vehicle_id": 0},
        {"message": "Check my maintenance status.", "session": "client"},
        {
            "message": "Give me the experimental maintenance prediction.",
            "predictive_maintenance_input": {
                **predictive_payload(),
                "current_odometer_km": 1_000.0,
                "distance_since_last_scheduled_service_km": 2_000.0,
            },
        },
    ],
)
def test_unified_endpoint_rejects_invalid_request_bodies(
    assistant_client: tuple[TestClient, AssistantFakes],
    payload: dict[str, object],
) -> None:
    client, fakes = assistant_client

    response = client.post("/assistant/query", json=payload)

    assert response.status_code == 422
    assert fakes.maintenance.calls == []
    assert fakes.rag.questions == []
    assert fakes.escalation.calls == []
    assert fakes.predictive.inputs == []


def test_unified_support_provider_error_uses_existing_http_semantics(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client
    fakes.rag.error = GeminiGenerationError("internal provider detail")

    response = client.post(
        "/assistant/query",
        json={"message": "What does the tire pressure warning light mean?"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Support answer provider could not generate a response"
    }


def test_unified_predictive_error_uses_existing_http_semantics(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, fakes = assistant_client
    fakes.predictive.error = ExperimentalMaintenancePredictionError("internal")

    response = client.post(
        "/assistant/query",
        json={
            "message": "Give me the experimental maintenance prediction.",
            "predictive_maintenance_input": predictive_payload(),
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Experimental maintenance comparison is unavailable"
    }


def test_existing_health_and_direct_maintenance_endpoints_still_work(
    assistant_client: tuple[TestClient, AssistantFakes],
) -> None:
    client, _ = assistant_client

    health_response = client.get("/health")
    maintenance_response = client.post(
        "/maintenance/evaluate",
        json={
            "current_odometer_km": 5_000,
            "last_service_odometer_km": 1_000,
            "months_since_last_service": 4,
            "service_interval_km": 10_000,
            "service_interval_months": 12,
            "due_soon_threshold_percent": 80,
        },
    )

    assert health_response.status_code == 200
    assert maintenance_response.status_code == 200
    assert maintenance_response.json()["status"] == "not_due"


def test_openapi_schema_includes_typed_unified_endpoint() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    operation = schema["paths"]["/assistant/query"]["post"]
    assert operation["requestBody"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/AssistantQueryRequest"}
    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/AssistantQueryResponse"}
