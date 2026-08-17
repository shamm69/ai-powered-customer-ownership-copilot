"""Tests for Phase 4 orchestration and stored maintenance integration."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.escalation import EscalationReason, HandoffStatus, HumanHandoffResult
from app.grounded_answers import AnswerSource, GroundedAnswer, UNSUPPORTED_ANSWER
from app.maintenance import MaintenanceDueResult, MaintenanceStatus
from app.maintenance_service import (
    ScheduledServiceNotFoundError,
    VehicleNotFoundError,
)
from app.predictive_maintenance_comparison import (
    MaintenancePredictionComparison,
    MaintenanceSignalRelationship,
)
from app.predictive_maintenance_prediction import (
    ExperimentalMaintenancePrediction,
    PredictiveMaintenanceFeatureInput,
)
from app.orchestrator import (
    OrchestratedCapability,
    OrchestrationContext,
    OrchestrationContextField,
    OrchestrationOutcome,
    OrchestrationResult,
    orchestrate_user_request,
)
from app.routing import RoutingIntent
from app.retrieval_confidence import RetrievalSupportStatus


class FakeRagService:
    def __init__(
        self,
        result: GroundedAnswer | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.questions: list[str] = []

    def answer_question(self, question: str) -> GroundedAnswer:
        self.questions.append(question)
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise AssertionError("Fake RAG service requires a result")
        return self.result


class FakeEscalationService:
    def __init__(
        self,
        result: HumanHandoffResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[str, EscalationReason]] = []

    def __call__(
        self,
        user_request: str,
        reason: EscalationReason,
    ) -> HumanHandoffResult:
        self.calls.append((user_request, reason))
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise AssertionError("Fake escalation service requires a result")
        return self.result


class FakePredictiveComparisonService:
    def __init__(
        self,
        result: MaintenancePredictionComparison | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.inputs: list[PredictiveMaintenanceFeatureInput] = []

    def compare(
        self,
        feature_input: PredictiveMaintenanceFeatureInput,
    ) -> MaintenancePredictionComparison:
        self.inputs.append(feature_input)
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise AssertionError("Fake comparison service requires a result")
        return self.result


def maintenance_result(
    status: MaintenanceStatus = MaintenanceStatus.DUE_SOON,
) -> MaintenanceDueResult:
    return MaintenanceDueResult(
        status=status,
        kilometres_travelled_since_last_service=8_000.0,
        kilometres_remaining=2_000.0,
        months_remaining=4.0,
        reasons=("Original deterministic result",),
    )


def complete_context() -> OrchestrationContext:
    return OrchestrationContext(
        vehicle_id=42,
        evaluation_date=date(2026, 8, 18),
        session=MagicMock(spec=Session),
    )


def grounded_support_result() -> GroundedAnswer:
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


def predictive_feature_input() -> PredictiveMaintenanceFeatureInput:
    return PredictiveMaintenanceFeatureInput(
        vehicle_age_years=6.0,
        current_odometer_km=72_000.0,
        distance_since_last_scheduled_service_km=7_500.0,
        months_since_last_scheduled_service=8.0,
        service_interval_km=10_000.0,
        service_interval_months=12.0,
        average_monthly_driving_km=1_100.0,
        usage_severity_score=0.65,
    )


def predictive_comparison_result() -> MaintenancePredictionComparison:
    return MaintenancePredictionComparison(
        deterministic_result=maintenance_result(MaintenanceStatus.DUE_SOON),
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


def predictive_context() -> OrchestrationContext:
    return OrchestrationContext(
        predictive_maintenance_input=predictive_feature_input()
    )


def test_maintenance_route_invokes_existing_application_service() -> None:
    expected_result = maintenance_result()
    context = complete_context()

    with patch(
        "app.orchestrator.evaluate_vehicle_maintenance",
        return_value=expected_result,
    ) as service:
        result = orchestrate_user_request(
            "Is my vehicle due for service?",
            context,
        )

    service.assert_called_once_with(
        session=context.session,
        vehicle_id=42,
        evaluation_date=date(2026, 8, 18),
    )
    assert result.outcome is OrchestrationOutcome.EXECUTED
    assert (
        result.invoked_capability
        is OrchestratedCapability.STORED_VEHICLE_MAINTENANCE
    )


def test_original_maintenance_result_is_preserved_without_recomputation() -> None:
    expected_result = maintenance_result(MaintenanceStatus.OVERDUE)

    result = orchestrate_user_request(
        "Check my maintenance status.",
        complete_context(),
        maintenance_service=lambda **_: expected_result,
    )

    assert result.maintenance_result is expected_result
    assert result.maintenance_result.status is MaintenanceStatus.OVERDUE
    assert result.maintenance_result.reasons == ("Original deterministic result",)


@pytest.mark.parametrize(
    ("context", "expected_missing"),
    [
        (
            OrchestrationContext(
                evaluation_date=date(2026, 8, 18),
                session=MagicMock(spec=Session),
            ),
            (OrchestrationContextField.VEHICLE_ID,),
        ),
        (
            OrchestrationContext(
                vehicle_id=42,
                session=MagicMock(spec=Session),
            ),
            (OrchestrationContextField.EVALUATION_DATE,),
        ),
        (
            OrchestrationContext(
                vehicle_id=42,
                evaluation_date=date(2026, 8, 18),
            ),
            (OrchestrationContextField.DATABASE_SESSION,),
        ),
    ],
)
def test_missing_maintenance_context_does_not_invoke_service(
    context: OrchestrationContext,
    expected_missing: tuple[OrchestrationContextField, ...],
) -> None:
    service = MagicMock(side_effect=AssertionError("Service must not be called"))

    result = orchestrate_user_request(
        "Is my vehicle due for service?",
        context,
        maintenance_service=service,
    )

    service.assert_not_called()
    assert result.outcome is OrchestrationOutcome.CONTEXT_REQUIRED
    assert result.missing_context == expected_missing
    assert result.invoked_capability is None
    assert result.maintenance_result is None


def test_absent_context_reports_every_required_maintenance_value() -> None:
    result = orchestrate_user_request("Is my vehicle due for service?")

    assert result.outcome is OrchestrationOutcome.CONTEXT_REQUIRED
    assert result.missing_context == (
        OrchestrationContextField.VEHICLE_ID,
        OrchestrationContextField.EVALUATION_DATE,
        OrchestrationContextField.DATABASE_SESSION,
    )


@pytest.mark.parametrize(
    "service_error",
    [
        VehicleNotFoundError("Vehicle 42 was not found"),
        ScheduledServiceNotFoundError(
            "Vehicle 42 has no scheduled service record"
        ),
    ],
)
def test_known_maintenance_errors_propagate_unchanged(
    service_error: Exception,
) -> None:
    def failing_service(**_: object) -> MaintenanceDueResult:
        raise service_error

    with pytest.raises(type(service_error)) as captured:
        orchestrate_user_request(
            "Is my vehicle due for service?",
            complete_context(),
            maintenance_service=failing_service,
        )

    assert captured.value is service_error


def test_support_route_invokes_injected_rag_service_with_original_question(
) -> None:
    expected_result = grounded_support_result()
    service = FakeRagService(expected_result)
    question = "  What DOES the tire pressure warning light mean?  "

    result = orchestrate_user_request(question, rag_service=service)

    assert service.questions == [question]
    assert result.routing_decision.normalized_request == (
        "what does the tire pressure warning light mean"
    )
    assert result.outcome is OrchestrationOutcome.EXECUTED
    assert result.invoked_capability is OrchestratedCapability.SUPPORT_KNOWLEDGE


def test_support_route_preserves_exact_grounded_result_and_sources() -> None:
    expected_result = grounded_support_result()

    result = orchestrate_user_request(
        "What does the tire pressure warning light mean?",
        rag_service=FakeRagService(expected_result),
    )

    assert result.support_result is expected_result
    assert result.support_result.sources is expected_result.sources
    assert result.support_result.sources[0].chunk_id == (
        "tire-care.md::chunk-001"
    )
    assert result.maintenance_result is None


def test_unsupported_rag_result_is_preserved_without_fallback_changes() -> None:
    expected_result = GroundedAnswer(
        answer=UNSUPPORTED_ANSWER,
        retrieval_status=RetrievalSupportStatus.UNSUPPORTED,
        sources=(),
    )

    result = orchestrate_user_request(
        "What does the tire pressure warning light mean?",
        rag_service=FakeRagService(expected_result),
    )

    assert result.outcome is OrchestrationOutcome.EXECUTED
    assert result.support_result is expected_result
    assert result.support_result.answer == UNSUPPORTED_ANSWER
    assert result.support_result.sources == ()


def test_missing_rag_dependency_returns_explicit_context_required_outcome(
) -> None:
    result = orchestrate_user_request(
        "What does the tire pressure warning light mean?"
    )

    assert result.outcome is OrchestrationOutcome.CONTEXT_REQUIRED
    assert result.missing_context == (OrchestrationContextField.RAG_SERVICE,)
    assert result.invoked_capability is None
    assert result.support_result is None


def test_support_route_does_not_invoke_maintenance_service() -> None:
    maintenance_service = MagicMock(
        side_effect=AssertionError("Maintenance service must not be called")
    )

    orchestrate_user_request(
        "What does the tire pressure warning light mean?",
        complete_context(),
        maintenance_service=maintenance_service,
        rag_service=FakeRagService(grounded_support_result()),
    )

    maintenance_service.assert_not_called()


@pytest.mark.parametrize(
    "rag_error",
    [ValueError("invalid RAG result"), RuntimeError("provider failure")],
)
def test_rag_errors_propagate_without_http_translation(
    rag_error: Exception,
) -> None:
    with pytest.raises(type(rag_error)) as captured:
        orchestrate_user_request(
            "What does the tire pressure warning light mean?",
            rag_service=FakeRagService(error=rag_error),
        )

    assert captured.value is rag_error


def test_handoff_route_invokes_injected_escalation_service() -> None:
    expected_result = handoff_result()
    service = FakeEscalationService(expected_result)
    user_message = "I want to speak to a person."

    result = orchestrate_user_request(
        user_message,
        escalation_service=service,
    )

    assert service.calls == [
        (user_message, EscalationReason.ROUTED_HUMAN_HANDOFF)
    ]
    assert result.outcome is OrchestrationOutcome.EXECUTED
    assert result.invoked_capability is OrchestratedCapability.HUMAN_HANDOFF
    assert result.escalation_result is expected_result


def test_safety_routed_handoff_invokes_same_bounded_service() -> None:
    service = FakeEscalationService(handoff_result())

    result = orchestrate_user_request(
        "My vehicle is unsafe to drive.",
        escalation_service=service,
    )

    assert result.routing_decision.intent is RoutingIntent.HUMAN_HANDOFF
    assert service.calls == [
        (
            "My vehicle is unsafe to drive.",
            EscalationReason.ROUTED_HUMAN_HANDOFF,
        )
    ]
    assert result.outcome is OrchestrationOutcome.EXECUTED


def test_handoff_preserves_exact_escalation_result() -> None:
    expected_result = handoff_result()

    result = orchestrate_user_request(
        "I want to speak to a person.",
        escalation_service=FakeEscalationService(expected_result),
    )

    assert result.escalation_result is expected_result
    assert result.maintenance_result is None
    assert result.support_result is None


def test_missing_escalation_dependency_requires_context() -> None:
    result = orchestrate_user_request("I want to speak to a person.")

    assert result.outcome is OrchestrationOutcome.CONTEXT_REQUIRED
    assert result.missing_context == (
        OrchestrationContextField.ESCALATION_SERVICE,
    )
    assert result.invoked_capability is None
    assert result.escalation_result is None


def test_handoff_invokes_neither_maintenance_nor_rag() -> None:
    maintenance_service = MagicMock(
        side_effect=AssertionError("Maintenance must not be called")
    )
    rag_service = FakeRagService(error=AssertionError("RAG must not be called"))

    orchestrate_user_request(
        "Please connect me to a human agent about my maintenance status.",
        complete_context(),
        maintenance_service=maintenance_service,
        rag_service=rag_service,
        escalation_service=FakeEscalationService(handoff_result()),
    )

    maintenance_service.assert_not_called()
    assert rag_service.questions == []


def test_escalation_error_propagates_without_http_translation() -> None:
    service_error = RuntimeError("handoff creation failed")

    with pytest.raises(RuntimeError) as captured:
        orchestrate_user_request(
            "I want to speak to a person.",
            escalation_service=FakeEscalationService(error=service_error),
        )

    assert captured.value is service_error


def test_explicit_experimental_route_invokes_comparison_service() -> None:
    expected_result = predictive_comparison_result()
    service = FakePredictiveComparisonService(expected_result)
    context = predictive_context()

    result = orchestrate_user_request(
        "Compare my maintenance status with the experimental ML model.",
        context,
        predictive_comparison_service=service,
    )

    assert service.inputs == [context.predictive_maintenance_input]
    assert service.inputs[0] is context.predictive_maintenance_input
    assert result.routing_decision.intent is (
        RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE
    )
    assert result.outcome is OrchestrationOutcome.EXECUTED
    assert result.invoked_capability is (
        OrchestratedCapability.EXPERIMENTAL_PREDICTIVE_MAINTENANCE_COMPARISON
    )


def test_exact_experimental_comparison_result_is_preserved() -> None:
    expected_result = predictive_comparison_result()

    result = orchestrate_user_request(
        "Give me the experimental predictive maintenance probability.",
        predictive_context(),
        predictive_comparison_service=FakePredictiveComparisonService(
            expected_result
        ),
    )

    assert result.experimental_comparison_result is expected_result
    assert result.maintenance_result is None
    assert result.support_result is None
    assert result.escalation_result is None


def test_missing_predictive_comparison_service_requires_context() -> None:
    result = orchestrate_user_request(
        "Give me the experimental predictive maintenance probability.",
        predictive_context(),
    )

    assert result.outcome is OrchestrationOutcome.CONTEXT_REQUIRED
    assert result.missing_context == (
        OrchestrationContextField.PREDICTIVE_COMPARISON_SERVICE,
    )
    assert result.experimental_comparison_result is None


def test_missing_predictive_input_requires_context_without_service_call() -> None:
    service = FakePredictiveComparisonService(predictive_comparison_result())

    result = orchestrate_user_request(
        "Give me the experimental predictive maintenance probability.",
        predictive_comparison_service=service,
    )

    assert service.inputs == []
    assert result.outcome is OrchestrationOutcome.CONTEXT_REQUIRED
    assert result.missing_context == (
        OrchestrationContextField.PREDICTIVE_MAINTENANCE_INPUT,
    )


def test_no_predictive_input_or_dependency_is_defaulted_or_fabricated() -> None:
    result = orchestrate_user_request(
        "Give me the experimental predictive maintenance probability."
    )

    assert result.outcome is OrchestrationOutcome.CONTEXT_REQUIRED
    assert result.missing_context == (
        OrchestrationContextField.PREDICTIVE_MAINTENANCE_INPUT,
        OrchestrationContextField.PREDICTIVE_COMPARISON_SERVICE,
    )
    assert result.invoked_capability is None


def test_ordinary_maintenance_never_invokes_predictive_comparison() -> None:
    comparison_service = FakePredictiveComparisonService(
        error=AssertionError("Experimental comparison must not be called")
    )

    result = orchestrate_user_request(
        "Is my vehicle due for service?",
        replace(
            complete_context(),
            predictive_maintenance_input=predictive_feature_input(),
        ),
        maintenance_service=lambda **_: maintenance_result(),
        predictive_comparison_service=comparison_service,
    )

    assert comparison_service.inputs == []
    assert result.invoked_capability is (
        OrchestratedCapability.STORED_VEHICLE_MAINTENANCE
    )
    assert result.maintenance_result is not None


def test_experimental_route_invokes_no_other_capability() -> None:
    maintenance_service = MagicMock(
        side_effect=AssertionError("Stored maintenance must not be called")
    )
    rag_service = FakeRagService(error=AssertionError("RAG must not be called"))
    escalation_service = MagicMock(
        side_effect=AssertionError("Escalation must not be called")
    )

    result = orchestrate_user_request(
        "Give me the experimental predictive maintenance probability.",
        predictive_context(),
        maintenance_service=maintenance_service,
        rag_service=rag_service,
        escalation_service=escalation_service,
        predictive_comparison_service=FakePredictiveComparisonService(
            predictive_comparison_result()
        ),
    )

    maintenance_service.assert_not_called()
    assert rag_service.questions == []
    escalation_service.assert_not_called()
    assert result.outcome is OrchestrationOutcome.EXECUTED


def test_predictive_comparison_error_propagates_without_http_translation() -> None:
    service_error = RuntimeError("experimental comparison failed")

    with pytest.raises(RuntimeError) as captured:
        orchestrate_user_request(
            "Give me the experimental predictive maintenance probability.",
            predictive_context(),
            predictive_comparison_service=FakePredictiveComparisonService(
                error=service_error
            ),
        )

    assert captured.value is service_error


@pytest.mark.parametrize(
    "request_text",
    [
        "Is my vehicle due for service?",
        "What does the tire pressure warning light mean?",
        "Give me the experimental predictive maintenance probability.",
        "Give me a pasta recipe.",
        "I need help with my car.",
    ],
)
def test_non_handoff_routes_never_invoke_escalation_service(
    request_text: str,
) -> None:
    escalation_service = MagicMock(
        side_effect=AssertionError("Escalation must not be called")
    )

    orchestrate_user_request(
        request_text,
        complete_context(),
        maintenance_service=lambda **_: maintenance_result(),
        rag_service=FakeRagService(grounded_support_result()),
        escalation_service=escalation_service,
    )

    escalation_service.assert_not_called()


def test_unsupported_route_has_explicit_outcome() -> None:
    result = orchestrate_user_request("Give me a pasta recipe.")

    assert result.routing_decision.intent is RoutingIntent.UNSUPPORTED
    assert result.outcome is OrchestrationOutcome.UNSUPPORTED
    assert result.invoked_capability is None


def test_classifier_clarification_remains_clarification() -> None:
    result = orchestrate_user_request("I need help with my car.")

    assert result.routing_decision.intent is RoutingIntent.CLARIFICATION_REQUIRED
    assert result.outcome is OrchestrationOutcome.CLARIFICATION_REQUIRED
    assert result.invoked_capability is None


@pytest.mark.parametrize(
    "request_text",
    [
        "What does the tire pressure warning light mean?",
        "Compare my maintenance status with the experimental ML model.",
        "I want to speak to a person.",
        "Give me a pasta recipe.",
        "I need help with my car.",
    ],
)
def test_non_maintenance_routes_never_invoke_maintenance_service(
    request_text: str,
) -> None:
    service = MagicMock(side_effect=AssertionError("Unexpected maintenance call"))

    orchestrate_user_request(
        request_text,
        complete_context(),
        maintenance_service=service,
    )

    service.assert_not_called()


def test_experimental_route_cannot_create_hybrid_maintenance_result() -> None:
    expected_comparison = predictive_comparison_result()
    result = orchestrate_user_request(
        "Give me the experimental predictive maintenance probability.",
        predictive_context(),
        maintenance_service=MagicMock(
            side_effect=AssertionError("Deterministic service must not run")
        ),
        predictive_comparison_service=FakePredictiveComparisonService(
            expected_comparison
        ),
    )

    assert result.outcome is OrchestrationOutcome.EXECUTED
    assert result.maintenance_result is None
    assert result.experimental_comparison_result is expected_comparison
    assert set(field.name for field in fields(OrchestrationResult)) == {
        "routing_decision",
        "outcome",
        "invoked_capability",
        "maintenance_result",
        "support_result",
        "escalation_result",
        "experimental_comparison_result",
        "missing_context",
        "message",
    }


def test_orchestration_result_and_context_are_immutable() -> None:
    context = complete_context()
    original_context = replace(context)
    result = orchestrate_user_request(
        "Check my maintenance status.",
        context,
        maintenance_service=lambda **_: maintenance_result(),
    )

    assert context == original_context
    with pytest.raises(FrozenInstanceError):
        result.outcome = OrchestrationOutcome.UNSUPPORTED  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        context.vehicle_id = 99  # type: ignore[misc]
