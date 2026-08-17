"""Deterministic routing vocabulary and intent classification boundary."""

from dataclasses import dataclass
from enum import Enum


class RoutingIntent(str, Enum):
    """Supported routing outcomes before any tool or service invocation."""

    STORED_VEHICLE_MAINTENANCE = "stored_vehicle_maintenance"
    SUPPORT_KNOWLEDGE = "support_knowledge"
    EXPERIMENTAL_PREDICTIVE_MAINTENANCE = (
        "experimental_predictive_maintenance"
    )
    HUMAN_HANDOFF = "human_handoff"
    UNSUPPORTED = "unsupported"
    CLARIFICATION_REQUIRED = "clarification_required"


@dataclass(frozen=True)
class RoutingDecision:
    """Explainable intent classification without executing a route."""

    intent: RoutingIntent
    normalized_request: str
    matched_intents: tuple[RoutingIntent, ...]
    reason: str


_HANDOFF_PHRASES = (
    "customer service representative",
    "escalate to a human",
    "human agent",
    "human handoff",
    "human support",
    "live agent",
    "speak to a person",
    "support representative",
    "talk to a person",
)

_SAFETY_HANDOFF_PHRASES = (
    "immediate safety concern",
    "safety emergency",
    "unsafe to drive",
)

_MAINTENANCE_PHRASES = (
    "check my maintenance",
    "check my service",
    "due for maintenance",
    "due for service",
    "maintenance status",
    "my next service",
    "next maintenance due",
    "next service due",
    "service status",
)

_DOCUMENTATION_PHRASES = (
    "knowledge base",
    "owner manual",
    "owner's manual",
    "service documentation",
    "support documentation",
    "support guide",
)

_SUPPORT_QUESTION_PHRASES = (
    "explain",
    "how do i",
    "how often",
    "how should",
    "tell me about",
    "what does",
    "where can i find",
)

_SUPPORT_TOPIC_PHRASES = (
    "battery care",
    "fluid level",
    "fluid levels",
    "service interval",
    "tire pressure",
    "warning light",
)

_EXPERIMENTAL_MARKERS = (
    "experimental",
    "logistic regression",
    "machine learning",
    "ml model",
)

_EXPERIMENTAL_ACTIONS = (
    "compare",
    "comparison",
    "predict",
    "prediction",
    "predictive",
    "probability",
    "risk score",
)

_MAINTENANCE_CONTEXT = (
    "maintenance",
    "service",
    "vehicle",
)

_VAGUE_DOMAIN_WORDS = {
    "car",
    "documentation",
    "help",
    "maintenance",
    "manual",
    "service",
    "support",
    "vehicle",
}


def normalize_routing_request(user_request: str) -> str:
    """Case-fold text, replace punctuation with spaces, and collapse whitespace."""
    if not isinstance(user_request, str):
        raise TypeError("user_request must be a string")
    characters = (
        character if character.isalnum() or character == "'" else " "
        for character in user_request.casefold()
    )
    return " ".join("".join(characters).split())


def classify_routing_intent(user_request: str) -> RoutingDecision:
    """Classify one request using small explicit rules without invoking tools."""
    normalized_request = normalize_routing_request(user_request)
    if not normalized_request:
        return _decision(
            RoutingIntent.CLARIFICATION_REQUIRED,
            normalized_request,
            (),
            "The request is empty and needs clarification.",
        )

    if _matches_handoff(normalized_request):
        return _decision(
            RoutingIntent.HUMAN_HANDOFF,
            normalized_request,
            (RoutingIntent.HUMAN_HANDOFF,),
            "The request explicitly asks for human help or states a safety concern.",
        )

    experimental_match = _matches_experimental_predictive_maintenance(
        normalized_request
    )
    support_match = _matches_support_knowledge(normalized_request)

    if experimental_match:
        if support_match:
            return _ambiguous_decision(
                normalized_request,
                (
                    RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE,
                    RoutingIntent.SUPPORT_KNOWLEDGE,
                ),
            )
        return _decision(
            RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE,
            normalized_request,
            (RoutingIntent.EXPERIMENTAL_PREDICTIVE_MAINTENANCE,),
            "The request explicitly asks for the experimental maintenance signal.",
        )

    maintenance_match = _matches_stored_vehicle_maintenance(normalized_request)
    matched_intents = tuple(
        intent
        for intent, matched in (
            (RoutingIntent.STORED_VEHICLE_MAINTENANCE, maintenance_match),
            (RoutingIntent.SUPPORT_KNOWLEDGE, support_match),
        )
        if matched
    )
    if len(matched_intents) > 1:
        return _ambiguous_decision(normalized_request, matched_intents)
    if matched_intents:
        intent = matched_intents[0]
        reason = (
            "The request asks for stored-vehicle maintenance status."
            if intent is RoutingIntent.STORED_VEHICLE_MAINTENANCE
            else "The request asks for automotive support information."
        )
        return _decision(
            intent,
            normalized_request,
            matched_intents,
            reason,
        )

    words = set(normalized_request.split())
    if words & _VAGUE_DOMAIN_WORDS:
        return _decision(
            RoutingIntent.CLARIFICATION_REQUIRED,
            normalized_request,
            (),
            "The automotive request does not identify one clear route.",
        )
    return _decision(
        RoutingIntent.UNSUPPORTED,
        normalized_request,
        (),
        "The request is outside the supported automotive routing scope.",
    )


def _matches_handoff(normalized_request: str) -> bool:
    return _contains_any_phrase(
        normalized_request,
        _HANDOFF_PHRASES + _SAFETY_HANDOFF_PHRASES,
    )


def _matches_stored_vehicle_maintenance(normalized_request: str) -> bool:
    return _contains_any_phrase(normalized_request, _MAINTENANCE_PHRASES)


def _matches_support_knowledge(normalized_request: str) -> bool:
    if _contains_any_phrase(normalized_request, _DOCUMENTATION_PHRASES):
        return True
    return _contains_any_phrase(
        normalized_request,
        _SUPPORT_QUESTION_PHRASES,
    ) and _contains_any_phrase(normalized_request, _SUPPORT_TOPIC_PHRASES)


def _matches_experimental_predictive_maintenance(
    normalized_request: str,
) -> bool:
    return (
        _contains_any_phrase(normalized_request, _EXPERIMENTAL_MARKERS)
        and _contains_any_phrase(normalized_request, _EXPERIMENTAL_ACTIONS)
        and _contains_any_phrase(normalized_request, _MAINTENANCE_CONTEXT)
    )


def _contains_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    padded_text = f" {text} "
    return any(f" {phrase} " in padded_text for phrase in phrases)


def _ambiguous_decision(
    normalized_request: str,
    matched_intents: tuple[RoutingIntent, ...],
) -> RoutingDecision:
    return _decision(
        RoutingIntent.CLARIFICATION_REQUIRED,
        normalized_request,
        matched_intents,
        "The request matches multiple routes and needs clarification.",
    )


def _decision(
    intent: RoutingIntent,
    normalized_request: str,
    matched_intents: tuple[RoutingIntent, ...],
    reason: str,
) -> RoutingDecision:
    return RoutingDecision(
        intent=intent,
        normalized_request=normalized_request,
        matched_intents=matched_intents,
        reason=reason,
    )
