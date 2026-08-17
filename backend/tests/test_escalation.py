"""Tests for deterministic mock human-handoff creation."""

from dataclasses import FrozenInstanceError

import pytest

from app.escalation import (
    EscalationReason,
    HandoffStatus,
    HumanHandoffResult,
    create_human_handoff,
)


def test_creates_typed_handoff_with_injected_ticket_identifier() -> None:
    result = create_human_handoff(
        "Please connect me to a person.",
        EscalationReason.ROUTED_HUMAN_HANDOFF,
        ticket_id_generator=lambda: "handoff-fixed-001",
    )

    assert result == HumanHandoffResult(
        ticket_id="handoff-fixed-001",
        reason=EscalationReason.ROUTED_HUMAN_HANDOFF,
        request_summary="Please connect me to a person.",
        status=HandoffStatus.CREATED,
    )


def test_preserves_trimmed_original_request_as_summary() -> None:
    result = create_human_handoff(
        "  My vehicle is unsafe to drive.  ",
        EscalationReason.ROUTED_HUMAN_HANDOFF,
        ticket_id_generator=lambda: "safety-001",
    )

    assert result.request_summary == "My vehicle is unsafe to drive."


def test_ticket_identifier_generator_is_called_once() -> None:
    generated_identifiers = iter(("first-id", "unexpected-second-id"))

    result = create_human_handoff(
        "I want a human agent.",
        EscalationReason.ROUTED_HUMAN_HANDOFF,
        ticket_id_generator=lambda: next(generated_identifiers),
    )

    assert result.ticket_id == "first-id"
    assert next(generated_identifiers) == "unexpected-second-id"


@pytest.mark.parametrize("user_request", ["", "   ", "\n\t", None])
def test_blank_or_invalid_request_is_rejected(user_request: object) -> None:
    with pytest.raises(ValueError, match="user_request must not be empty"):
        create_human_handoff(
            user_request,  # type: ignore[arg-type]
            EscalationReason.ROUTED_HUMAN_HANDOFF,
            ticket_id_generator=lambda: "unused-id",
        )


@pytest.mark.parametrize("ticket_id", ["", "   ", None, 42])
def test_invalid_generated_ticket_identifier_is_rejected(
    ticket_id: object,
) -> None:
    with pytest.raises(ValueError, match="must return nonblank text"):
        create_human_handoff(
            "I want a human agent.",
            EscalationReason.ROUTED_HUMAN_HANDOFF,
            ticket_id_generator=lambda: ticket_id,  # type: ignore[return-value]
        )


def test_handoff_result_is_immutable() -> None:
    result = create_human_handoff(
        "I want a human agent.",
        EscalationReason.ROUTED_HUMAN_HANDOFF,
        ticket_id_generator=lambda: "handoff-fixed-001",
    )

    with pytest.raises(FrozenInstanceError):
        result.status = HandoffStatus.CREATED  # type: ignore[misc]
