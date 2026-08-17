"""Explicit orchestration with stored maintenance as the first integrated tool."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Protocol

from sqlalchemy.orm import Session

from app.maintenance import MaintenanceDueResult
from app.maintenance_service import evaluate_vehicle_maintenance
from app.routing import RoutingDecision, RoutingIntent, classify_routing_intent


class OrchestrationOutcome(str, Enum):
    """Execution outcomes understood before a unified API is added."""

    EXECUTED = "executed"
    CONTEXT_REQUIRED = "context_required"
    NOT_YET_INTEGRATED = "not_yet_integrated"
    UNSUPPORTED = "unsupported"
    CLARIFICATION_REQUIRED = "clarification_required"


class OrchestratedCapability(str, Enum):
    """Capabilities the orchestrator can currently invoke."""

    STORED_VEHICLE_MAINTENANCE = "stored_vehicle_maintenance"


class OrchestrationContextField(str, Enum):
    """Explicit context values needed for tool execution."""

    VEHICLE_ID = "vehicle_id"
    EVALUATION_DATE = "evaluation_date"
    DATABASE_SESSION = "database_session"


@dataclass(frozen=True)
class OrchestrationContext:
    """Context supplied by a future HTTP or application boundary."""

    vehicle_id: int | None = None
    evaluation_date: date | None = None
    session: Session | None = None


@dataclass(frozen=True)
class OrchestrationResult:
    """Typed routing and execution result without a generic payload."""

    routing_decision: RoutingDecision
    outcome: OrchestrationOutcome
    invoked_capability: OrchestratedCapability | None
    maintenance_result: MaintenanceDueResult | None
    missing_context: tuple[OrchestrationContextField, ...]
    message: str


class StoredVehicleMaintenanceService(Protocol):
    """Callable boundary matching the existing maintenance application service."""

    def __call__(
        self,
        session: Session,
        vehicle_id: int,
        evaluation_date: date,
    ) -> MaintenanceDueResult:
        """Evaluate one stored vehicle without changing its domain result."""
        ...


def orchestrate_user_request(
    user_message: str,
    context: OrchestrationContext | None = None,
    *,
    maintenance_service: StoredVehicleMaintenanceService | None = None,
) -> OrchestrationResult:
    """Classify a request and execute only stored-vehicle maintenance."""
    routing_decision = classify_routing_intent(user_message)
    resolved_context = context or OrchestrationContext()

    if routing_decision.intent is RoutingIntent.STORED_VEHICLE_MAINTENANCE:
        return _execute_stored_vehicle_maintenance(
            routing_decision,
            resolved_context,
            maintenance_service,
        )
    return _non_maintenance_result(routing_decision)


def _execute_stored_vehicle_maintenance(
    routing_decision: RoutingDecision,
    context: OrchestrationContext,
    maintenance_service: StoredVehicleMaintenanceService | None,
) -> OrchestrationResult:
    missing_context = _missing_maintenance_context(context)
    if missing_context:
        return OrchestrationResult(
            routing_decision=routing_decision,
            outcome=OrchestrationOutcome.CONTEXT_REQUIRED,
            invoked_capability=None,
            maintenance_result=None,
            missing_context=missing_context,
            message="Stored-vehicle maintenance requires additional context.",
        )

    session = context.session
    vehicle_id = context.vehicle_id
    evaluation_date = context.evaluation_date
    if session is None or vehicle_id is None or evaluation_date is None:
        raise RuntimeError("Maintenance context validation was inconsistent")

    service = (
        maintenance_service
        if maintenance_service is not None
        else evaluate_vehicle_maintenance
    )
    maintenance_result = service(
        session=session,
        vehicle_id=vehicle_id,
        evaluation_date=evaluation_date,
    )
    return OrchestrationResult(
        routing_decision=routing_decision,
        outcome=OrchestrationOutcome.EXECUTED,
        invoked_capability=OrchestratedCapability.STORED_VEHICLE_MAINTENANCE,
        maintenance_result=maintenance_result,
        missing_context=(),
        message="Stored-vehicle maintenance was evaluated deterministically.",
    )


def _missing_maintenance_context(
    context: OrchestrationContext,
) -> tuple[OrchestrationContextField, ...]:
    required_values = (
        (OrchestrationContextField.VEHICLE_ID, context.vehicle_id),
        (OrchestrationContextField.EVALUATION_DATE, context.evaluation_date),
        (OrchestrationContextField.DATABASE_SESSION, context.session),
    )
    return tuple(field for field, value in required_values if value is None)


def _non_maintenance_result(
    routing_decision: RoutingDecision,
) -> OrchestrationResult:
    intent = routing_decision.intent
    if intent is RoutingIntent.SUPPORT_KNOWLEDGE:
        return _unexecuted_result(
            routing_decision,
            OrchestrationOutcome.NOT_YET_INTEGRATED,
            "Support knowledge routing is recognized but not yet integrated.",
        )
    if intent is RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE:
        return _unexecuted_result(
            routing_decision,
            OrchestrationOutcome.NOT_YET_INTEGRATED,
            "Experimental predictive maintenance is recognized but not executed.",
        )
    if intent is RoutingIntent.HUMAN_HANDOFF:
        return _unexecuted_result(
            routing_decision,
            OrchestrationOutcome.NOT_YET_INTEGRATED,
            "Human handoff is recognized but escalation is not yet integrated.",
        )
    if intent is RoutingIntent.UNSUPPORTED:
        return _unexecuted_result(
            routing_decision,
            OrchestrationOutcome.UNSUPPORTED,
            "The request is outside the supported orchestration scope.",
        )
    if intent is RoutingIntent.CLARIFICATION_REQUIRED:
        return _unexecuted_result(
            routing_decision,
            OrchestrationOutcome.CLARIFICATION_REQUIRED,
            "The request requires clarification before any capability is invoked.",
        )
    raise ValueError(f"Unhandled routing intent: {intent}")


def _unexecuted_result(
    routing_decision: RoutingDecision,
    outcome: OrchestrationOutcome,
    message: str,
) -> OrchestrationResult:
    return OrchestrationResult(
        routing_decision=routing_decision,
        outcome=outcome,
        invoked_capability=None,
        maintenance_result=None,
        missing_context=(),
        message=message,
    )
