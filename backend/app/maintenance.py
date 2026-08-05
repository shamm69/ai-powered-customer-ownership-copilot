"""Deterministic scheduled-maintenance domain logic."""

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class MaintenanceStatus(str, Enum):
    """Possible scheduled-service due states."""

    NOT_DUE = "not_due"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"


@dataclass(frozen=True)
class MaintenanceDueResult:
    """Explainable result of evaluating a scheduled-service interval."""

    status: MaintenanceStatus
    kilometres_travelled_since_last_service: float
    kilometres_remaining: float
    months_remaining: float
    reasons: tuple[str, ...]


def evaluate_maintenance_due_status(
    current_odometer_km: float,
    last_service_odometer_km: float,
    months_since_last_service: float,
    service_interval_km: float,
    service_interval_months: float,
    due_soon_threshold_percent: float,
) -> MaintenanceDueResult:
    """Evaluate scheduled-service urgency using distance and time intervals."""
    values = {
        "current_odometer_km": current_odometer_km,
        "last_service_odometer_km": last_service_odometer_km,
        "months_since_last_service": months_since_last_service,
        "service_interval_km": service_interval_km,
        "service_interval_months": service_interval_months,
        "due_soon_threshold_percent": due_soon_threshold_percent,
    }
    for name, value in values.items():
        if not isfinite(value):
            raise ValueError(f"{name} must be a finite number")

    non_negative_values = {
        "current_odometer_km": current_odometer_km,
        "last_service_odometer_km": last_service_odometer_km,
        "months_since_last_service": months_since_last_service,
    }
    for name, value in non_negative_values.items():
        if value < 0:
            raise ValueError(f"{name} must not be negative")

    if current_odometer_km < last_service_odometer_km:
        raise ValueError(
            "current_odometer_km must not be lower than last_service_odometer_km"
        )
    if service_interval_km <= 0:
        raise ValueError("service_interval_km must be greater than zero")
    if service_interval_months <= 0:
        raise ValueError("service_interval_months must be greater than zero")
    if not 0 < due_soon_threshold_percent < 100:
        raise ValueError(
            "due_soon_threshold_percent must be greater than 0 and less than 100"
        )

    kilometres_travelled = current_odometer_km - last_service_odometer_km
    kilometres_remaining = service_interval_km - kilometres_travelled
    months_remaining = service_interval_months - months_since_last_service

    distance_is_overdue = kilometres_travelled >= service_interval_km
    time_is_overdue = months_since_last_service >= service_interval_months

    if distance_is_overdue or time_is_overdue:
        reasons: list[str] = []
        if distance_is_overdue:
            reasons.append(
                "Distance caused overdue status: the distance service interval "
                "has been reached or exceeded."
            )
        if time_is_overdue:
            reasons.append(
                "Time caused overdue status: the time service interval has been "
                "reached or exceeded."
            )
        return MaintenanceDueResult(
            status=MaintenanceStatus.OVERDUE,
            kilometres_travelled_since_last_service=kilometres_travelled,
            kilometres_remaining=kilometres_remaining,
            months_remaining=months_remaining,
            reasons=tuple(reasons),
        )

    threshold_ratio = due_soon_threshold_percent / 100
    distance_is_due_soon = (
        kilometres_travelled >= service_interval_km * threshold_ratio
    )
    time_is_due_soon = (
        months_since_last_service >= service_interval_months * threshold_ratio
    )

    if distance_is_due_soon or time_is_due_soon:
        reasons = []
        if distance_is_due_soon:
            reasons.append(
                "Distance caused due_soon status: the distance due-soon threshold "
                "has been reached or exceeded."
            )
        if time_is_due_soon:
            reasons.append(
                "Time caused due_soon status: the time due-soon threshold has been "
                "reached or exceeded."
            )
        return MaintenanceDueResult(
            status=MaintenanceStatus.DUE_SOON,
            kilometres_travelled_since_last_service=kilometres_travelled,
            kilometres_remaining=kilometres_remaining,
            months_remaining=months_remaining,
            reasons=tuple(reasons),
        )

    return MaintenanceDueResult(
        status=MaintenanceStatus.NOT_DUE,
        kilometres_travelled_since_last_service=kilometres_travelled,
        kilometres_remaining=kilometres_remaining,
        months_remaining=months_remaining,
        reasons=(
            "Neither distance nor time caused a due status: both remain below the "
            "due-soon threshold.",
        ),
    )
