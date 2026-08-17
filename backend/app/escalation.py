"""Deterministic mock human-handoff creation without external integration."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from uuid import uuid4


class EscalationReason(str, Enum):
    """Reason category supplied after deterministic routing has completed."""

    ROUTED_HUMAN_HANDOFF = "routed_human_handoff"


class HandoffStatus(str, Enum):
    """Lifecycle state represented by the bounded mock service."""

    CREATED = "created"


@dataclass(frozen=True)
class HumanHandoffResult:
    """Immutable record of a mock handoff accepted for human follow-up."""

    ticket_id: str
    reason: EscalationReason
    request_summary: str
    status: HandoffStatus


TicketIdGenerator = Callable[[], str]


def _generate_ticket_id() -> str:
    return f"handoff-{uuid4().hex}"


def create_human_handoff(
    user_request: str,
    reason: EscalationReason,
    *,
    ticket_id_generator: TicketIdGenerator = _generate_ticket_id,
) -> HumanHandoffResult:
    """Create one in-memory handoff result from an already-routed request."""
    if not isinstance(user_request, str) or not user_request.strip():
        raise ValueError("user_request must not be empty or blank")
    if not isinstance(reason, EscalationReason):
        raise ValueError("reason must be an EscalationReason")

    ticket_id = ticket_id_generator()
    if not isinstance(ticket_id, str) or not ticket_id.strip():
        raise ValueError("ticket ID generator must return nonblank text")

    return HumanHandoffResult(
        ticket_id=ticket_id.strip(),
        reason=reason,
        request_summary=user_request.strip(),
        status=HandoffStatus.CREATED,
    )
