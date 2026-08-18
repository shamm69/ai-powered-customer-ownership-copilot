"""Deterministic service-type recommendations for stored demo vehicles."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from sqlalchemy.orm import Session

from app.maintenance import MaintenanceDueResult, MaintenanceStatus
from app.maintenance_service import (
    MaintenanceServiceError,
    evaluate_vehicle_maintenance,
)
from app.queries import get_vehicle_by_id

# Demo/MVP inspection rules, not manufacturer-authoritative service schedules.
TYRE_INSPECTION_DISTANCE_KM = 8_000.0
BATTERY_HEALTH_CHECK_AGE_YEARS = 5


class ServiceType(str, Enum):
    """Predefined service and preventive-inspection categories."""

    PERIODIC_MAINTENANCE = "periodic_maintenance_service"
    PRE_TRIP_INSPECTION = "pre_trip_inspection"
    TYRE_INSPECTION_ROTATION = "tyre_inspection_rotation"
    BATTERY_HEALTH_CHECK = "battery_health_check"
    NO_SERVICE_REQUIRED = "no_service_required"


class RecommendationPriority(str, Enum):
    """Explainable urgency for a service recommendation."""

    NONE = "none"
    ROUTINE = "routine"
    RECOMMENDED = "recommended"
    DUE_SOON = "due_soon"
    URGENT = "urgent"


class RecommendationContext(str, Enum):
    """Explicit user context that may support a preventive inspection."""

    GENERAL = "general"
    LONG_TRIP = "long_trip"


@dataclass(frozen=True)
class ServiceRecommendation:
    """One specific, explainable service or inspection category."""

    service_type: ServiceType
    priority: RecommendationPriority
    reason: str
    supporting_factors: tuple[str, ...]


@dataclass(frozen=True)
class ServiceRecommendationResult:
    """Authoritative maintenance context plus ordered next-service options."""

    maintenance_result: MaintenanceDueResult
    recommendations: tuple[ServiceRecommendation, ...]


def recommend_vehicle_services(
    session: Session,
    vehicle_id: int,
    evaluation_date: date,
    recommendation_context: RecommendationContext = RecommendationContext.GENERAL,
) -> ServiceRecommendationResult:
    """Recommend bounded service types from stored and deterministic context."""
    maintenance_result = evaluate_vehicle_maintenance(
        session=session,
        vehicle_id=vehicle_id,
        evaluation_date=evaluation_date,
    )
    vehicle = get_vehicle_by_id(session, vehicle_id)
    if vehicle is None:
        raise MaintenanceServiceError(
            "Vehicle disappeared during service recommendation evaluation"
        )
    if evaluation_date.year < vehicle.model_year:
        raise MaintenanceServiceError(
            "evaluation_date must not be earlier than the vehicle model year"
        )

    vehicle_age_years = evaluation_date.year - vehicle.model_year
    recommendations: list[ServiceRecommendation] = []

    if maintenance_result.status is MaintenanceStatus.OVERDUE:
        recommendations.append(
            ServiceRecommendation(
                service_type=ServiceType.PERIODIC_MAINTENANCE,
                priority=RecommendationPriority.URGENT,
                reason=(
                    "The authoritative scheduled-maintenance evaluation is overdue."
                ),
                supporting_factors=maintenance_result.reasons,
            )
        )
    elif maintenance_result.status is MaintenanceStatus.DUE_SOON:
        recommendations.append(
            ServiceRecommendation(
                service_type=ServiceType.PERIODIC_MAINTENANCE,
                priority=RecommendationPriority.DUE_SOON,
                reason=(
                    "The authoritative scheduled-maintenance evaluation is due soon."
                ),
                supporting_factors=maintenance_result.reasons,
            )
        )

    if recommendation_context is RecommendationContext.LONG_TRIP:
        recommendations.append(
            ServiceRecommendation(
                service_type=ServiceType.PRE_TRIP_INSPECTION,
                priority=RecommendationPriority.RECOMMENDED,
                reason=(
                    "A preventive pre-trip inspection is appropriate before the "
                    "explicitly stated long trip; it does not indicate a fault."
                ),
                supporting_factors=("The customer explicitly mentioned a long trip.",),
            )
        )

    distance_since_service = (
        maintenance_result.kilometres_travelled_since_last_service
    )
    if distance_since_service >= TYRE_INSPECTION_DISTANCE_KM:
        recommendations.append(
            ServiceRecommendation(
                service_type=ServiceType.TYRE_INSPECTION_ROTATION,
                priority=RecommendationPriority.ROUTINE,
                reason=(
                    "A routine tyre inspection or rotation can be considered after "
                    "substantial travel since the latest scheduled service."
                ),
                supporting_factors=(
                    f"{distance_since_service:.0f} km travelled since the latest "
                    "scheduled service.",
                    f"Demo inspection threshold: {TYRE_INSPECTION_DISTANCE_KM:.0f} km.",
                ),
            )
        )

    if vehicle_age_years >= BATTERY_HEALTH_CHECK_AGE_YEARS:
        recommendations.append(
            ServiceRecommendation(
                service_type=ServiceType.BATTERY_HEALTH_CHECK,
                priority=RecommendationPriority.ROUTINE,
                reason=(
                    "A routine battery health check can be considered as the vehicle "
                    "ages; this is not a battery-failure diagnosis."
                ),
                supporting_factors=(
                    f"Model-year age at evaluation: {vehicle_age_years} years.",
                    "Demo inspection threshold: 5 years.",
                ),
            )
        )

    if not recommendations:
        recommendations.append(
            ServiceRecommendation(
                service_type=ServiceType.NO_SERVICE_REQUIRED,
                priority=RecommendationPriority.NONE,
                reason=(
                    "No current service type is justified by the scheduled-maintenance "
                    "result or the bounded demo inspection rules."
                ),
                supporting_factors=(
                    "Authoritative scheduled-maintenance status is not due.",
                ),
            )
        )

    return ServiceRecommendationResult(
        maintenance_result=maintenance_result,
        recommendations=tuple(recommendations),
    )
