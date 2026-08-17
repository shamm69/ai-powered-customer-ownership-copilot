"""Tests for deterministic Phase 4 routing classification."""

from dataclasses import FrozenInstanceError

import pytest

from app.routing import (
    RoutingIntent,
    classify_routing_intent,
    normalize_routing_request,
)


@pytest.mark.parametrize(
    "request_text",
    [
        "Is my vehicle due for service?",
        "Please check my maintenance status.",
        "When is my next service due?",
    ],
)
def test_clear_stored_vehicle_maintenance_intent(request_text: str) -> None:
    decision = classify_routing_intent(request_text)

    assert decision.intent is RoutingIntent.STORED_VEHICLE_MAINTENANCE
    assert decision.matched_intents == (
        RoutingIntent.STORED_VEHICLE_MAINTENANCE,
    )


@pytest.mark.parametrize(
    "request_text",
    [
        "What does the tire pressure warning light mean?",
        "Show me the support documentation for battery care.",
        "How often should I check fluid levels?",
    ],
)
def test_clear_support_knowledge_intent(request_text: str) -> None:
    decision = classify_routing_intent(request_text)

    assert decision.intent is RoutingIntent.SUPPORT_KNOWLEDGE


@pytest.mark.parametrize(
    "request_text",
    [
        "Compare my maintenance status with the experimental ML model.",
        "Give me the experimental predictive maintenance probability.",
        "Use machine learning to predict my vehicle maintenance risk score.",
    ],
)
def test_explicit_experimental_predictive_intent(request_text: str) -> None:
    decision = classify_routing_intent(request_text)

    assert decision.intent is RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE


@pytest.mark.parametrize(
    "request_text",
    [
        "I want to speak to a person.",
        "Please connect me to a human agent about my maintenance status.",
        "My vehicle is unsafe to drive.",
    ],
)
def test_explicit_human_handoff_or_safety_intent(request_text: str) -> None:
    decision = classify_routing_intent(request_text)

    assert decision.intent is RoutingIntent.HUMAN_HANDOFF


@pytest.mark.parametrize(
    "request_text",
    ["", "  \t\n ", "I need help with my car"],
)
def test_empty_or_vague_automotive_input_requires_clarification(
    request_text: str,
) -> None:
    decision = classify_routing_intent(request_text)

    assert decision.intent is RoutingIntent.CLARIFICATION_REQUIRED


@pytest.mark.parametrize(
    "request_text",
    [
        "What is the weather tomorrow?",
        "Give me a pasta recipe.",
        "Who won the football match?",
    ],
)
def test_clearly_out_of_scope_input_is_unsupported(request_text: str) -> None:
    decision = classify_routing_intent(request_text)

    assert decision.intent is RoutingIntent.UNSUPPORTED
    assert decision.matched_intents == ()


def test_case_whitespace_and_punctuation_are_normalized() -> None:
    decision = classify_routing_intent(
        "  WHAT   does the TIRE-pressure warning light mean?!  "
    )

    assert decision.intent is RoutingIntent.SUPPORT_KNOWLEDGE
    assert decision.normalized_request == (
        "what does the tire pressure warning light mean"
    )


def test_maintenance_and_documentation_conflict_requires_clarification() -> None:
    decision = classify_routing_intent(
        "Is my vehicle due for service, and what does the owner's manual say?"
    )

    assert decision.intent is RoutingIntent.CLARIFICATION_REQUIRED
    assert decision.matched_intents == (
        RoutingIntent.STORED_VEHICLE_MAINTENANCE,
        RoutingIntent.SUPPORT_KNOWLEDGE,
    )


def test_experimental_and_documentation_conflict_requires_clarification() -> None:
    decision = classify_routing_intent(
        "Compare experimental maintenance prediction with the support documentation."
    )

    assert decision.intent is RoutingIntent.CLARIFICATION_REQUIRED
    assert decision.matched_intents == (
        RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE,
        RoutingIntent.SUPPORT_KNOWLEDGE,
    )


def test_explicit_handoff_takes_precedence_over_topic_routing() -> None:
    decision = classify_routing_intent(
        "Please let me speak to a person about my maintenance status."
    )

    assert decision.intent is RoutingIntent.HUMAN_HANDOFF
    assert decision.matched_intents == (RoutingIntent.HUMAN_HANDOFF,)


@pytest.mark.parametrize(
    "request_text",
    [
        "Is my vehicle due for service?",
        "Please check my maintenance status.",
        "When is my next service due?",
    ],
)
def test_ordinary_maintenance_never_routes_to_experimental_ml(
    request_text: str,
) -> None:
    decision = classify_routing_intent(request_text)

    assert decision.intent is RoutingIntent.STORED_VEHICLE_MAINTENANCE
    assert (
        RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE
        not in decision.matched_intents
    )


def test_predictive_wording_without_explicit_ml_marker_does_not_route_to_ml() -> None:
    decision = classify_routing_intent("Predict my maintenance needs.")

    assert decision.intent is RoutingIntent.CLARIFICATION_REQUIRED
    assert (
        RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE
        not in decision.matched_intents
    )


def test_routing_decision_is_immutable() -> None:
    decision = classify_routing_intent("Is my vehicle due for service?")

    with pytest.raises(FrozenInstanceError):
        decision.intent = RoutingIntent.UNSUPPORTED  # type: ignore[misc]


def test_normalization_rejects_non_string_input() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        normalize_routing_request(42)  # type: ignore[arg-type]
