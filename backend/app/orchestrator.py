"""Explicit orchestration across integrated tools and services."""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Protocol

from sqlalchemy.orm import Session

from app.escalation import EscalationReason, HumanHandoffResult
from app.grounded_answers import GroundedAnswer
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
    SUPPORT_KNOWLEDGE = "support_knowledge"
    HUMAN_HANDOFF = "human_handoff"


class OrchestrationContextField(str, Enum):
    """Explicit context values needed for tool execution."""

    VEHICLE_ID = "vehicle_id"
    EVALUATION_DATE = "evaluation_date"
    DATABASE_SESSION = "database_session"
    RAG_SERVICE = "rag_service"
    ESCALATION_SERVICE = "escalation_service"


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
    support_result: GroundedAnswer | None
    escalation_result: HumanHandoffResult | None
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


class SupportKnowledgeService(Protocol):
    """Boundary matching the prepared RAG application service."""

    def answer_question(self, question: str) -> GroundedAnswer:
        """Answer one support question through the existing RAG pipeline."""
        ...


class HumanHandoffService(Protocol):
    """Callable boundary matching the mock escalation service."""

    def __call__(
        self,
        user_request: str,
        reason: EscalationReason,
    ) -> HumanHandoffResult:
        """Create one handoff after the router has selected that intent."""
        ...


def orchestrate_user_request(
    user_message: str,
    context: OrchestrationContext | None = None,
    *,
    maintenance_service: StoredVehicleMaintenanceService | None = None,
    rag_service: SupportKnowledgeService | None = None,
    escalation_service: HumanHandoffService | None = None,
) -> OrchestrationResult:
    """Classify a request and execute an integrated capability when available."""
    routing_decision = classify_routing_intent(user_message)
    resolved_context = context or OrchestrationContext()

    if routing_decision.intent is RoutingIntent.STORED_VEHICLE_MAINTENANCE:
        return _execute_stored_vehicle_maintenance(
            routing_decision,
            resolved_context,
            maintenance_service,
        )
    if routing_decision.intent is RoutingIntent.SUPPORT_KNOWLEDGE:
        return _execute_support_knowledge(
            user_message,
            routing_decision,
            rag_service,
        )
    if routing_decision.intent is RoutingIntent.HUMAN_HANDOFF:
        return _execute_human_handoff(
            user_message,
            routing_decision,
            escalation_service,
        )
    return _unexecuted_route_result(routing_decision)


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
            support_result=None,
            escalation_result=None,
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
        support_result=None,
        escalation_result=None,
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


def _execute_support_knowledge(
    user_message: str,
    routing_decision: RoutingDecision,
    rag_service: SupportKnowledgeService | None,
) -> OrchestrationResult:
    if rag_service is None:
        return OrchestrationResult(
            routing_decision=routing_decision,
            outcome=OrchestrationOutcome.CONTEXT_REQUIRED,
            invoked_capability=None,
            maintenance_result=None,
            support_result=None,
            escalation_result=None,
            missing_context=(OrchestrationContextField.RAG_SERVICE,),
            message="Support knowledge requires a prepared RAG service.",
        )

    support_result = rag_service.answer_question(user_message)
    return OrchestrationResult(
        routing_decision=routing_decision,
        outcome=OrchestrationOutcome.EXECUTED,
        invoked_capability=OrchestratedCapability.SUPPORT_KNOWLEDGE,
        maintenance_result=None,
        support_result=support_result,
        escalation_result=None,
        missing_context=(),
        message="The support question was answered from the knowledge service.",
    )


def _execute_human_handoff(
    user_message: str,
    routing_decision: RoutingDecision,
    escalation_service: HumanHandoffService | None,
) -> OrchestrationResult:
    if escalation_service is None:
        return OrchestrationResult(
            routing_decision=routing_decision,
            outcome=OrchestrationOutcome.CONTEXT_REQUIRED,
            invoked_capability=None,
            maintenance_result=None,
            support_result=None,
            escalation_result=None,
            missing_context=(OrchestrationContextField.ESCALATION_SERVICE,),
            message="Human handoff requires an escalation service.",
        )

    escalation_result = escalation_service(
        user_request=user_message,
        reason=EscalationReason.ROUTED_HUMAN_HANDOFF,
    )
    return OrchestrationResult(
        routing_decision=routing_decision,
        outcome=OrchestrationOutcome.EXECUTED,
        invoked_capability=OrchestratedCapability.HUMAN_HANDOFF,
        maintenance_result=None,
        support_result=None,
        escalation_result=escalation_result,
        missing_context=(),
        message="A mock human handoff was created.",
    )


def _unexecuted_route_result(
    routing_decision: RoutingDecision,
) -> OrchestrationResult:
    intent = routing_decision.intent
    if intent is RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE:
        return _unexecuted_result(
            routing_decision,
            OrchestrationOutcome.NOT_YET_INTEGRATED,
            "Experimental predictive maintenance is recognized but not executed.",
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
        support_result=None,
        escalation_result=None,
        missing_context=(),
        message=message,
    )
