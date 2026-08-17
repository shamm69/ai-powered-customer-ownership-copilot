"""Tests for Phase 4 orchestration and stored maintenance integration."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.maintenance import MaintenanceDueResult, MaintenanceStatus
from app.maintenance_service import (
    ScheduledServiceNotFoundError,
    VehicleNotFoundError,
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


@pytest.mark.parametrize(
    ("request_text", "expected_intent"),
    [
        (
            "What does the tire pressure warning light mean?",
            RoutingIntent.SUPPORT_KNOWLEDGE,
        ),
        (
            "Compare my maintenance status with the experimental ML model.",
            RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE,
        ),
        ("I want to speak to a person.", RoutingIntent.HUMAN_HANDOFF),
    ],
)
def test_recognized_later_routes_are_not_yet_executed(
    request_text: str,
    expected_intent: RoutingIntent,
) -> None:
    result = orchestrate_user_request(request_text)

    assert result.routing_decision.intent is expected_intent
    assert result.outcome is OrchestrationOutcome.NOT_YET_INTEGRATED
    assert result.invoked_capability is None
    assert result.maintenance_result is None


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
    result = orchestrate_user_request(
        "Give me the experimental predictive maintenance probability.",
        complete_context(),
        maintenance_service=MagicMock(
            side_effect=AssertionError("Deterministic service must not run")
        ),
    )

    assert result.outcome is OrchestrationOutcome.NOT_YET_INTEGRATED
    assert result.maintenance_result is None
    assert set(field.name for field in fields(OrchestrationResult)) == {
        "routing_decision",
        "outcome",
        "invoked_capability",
        "maintenance_result",
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
