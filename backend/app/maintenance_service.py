"""Application layer connecting stored vehicle data to maintenance logic."""

from datetime import date

from sqlalchemy.orm import Session

from app.maintenance import MaintenanceDueResult, evaluate_maintenance_due_status
from app.queries import get_latest_scheduled_service, get_vehicle_by_id

DEFAULT_DUE_SOON_THRESHOLD_PERCENT = 80.0


class MaintenanceServiceError(ValueError):
    """Raised when stored data cannot support a maintenance evaluation."""


class VehicleNotFoundError(MaintenanceServiceError):
    """Raised when a requested vehicle does not exist."""


class ScheduledServiceNotFoundError(MaintenanceServiceError):
    """Raised when a vehicle has no scheduled service record."""


def _completed_months_between(service_date: date, evaluation_date: date) -> int:
    """Return whole calendar months elapsed between two dates."""
    if evaluation_date < service_date:
        raise MaintenanceServiceError(
            "evaluation_date must not be earlier than the latest scheduled service"
        )

    months = (evaluation_date.year - service_date.year) * 12
    months += evaluation_date.month - service_date.month
    if evaluation_date.day < service_date.day:
        months -= 1
    return months


def evaluate_vehicle_maintenance(
    session: Session,
    vehicle_id: int,
    evaluation_date: date,
    due_soon_threshold_percent: float = DEFAULT_DUE_SOON_THRESHOLD_PERCENT,
) -> MaintenanceDueResult:
    """Evaluate maintenance status using a stored vehicle and service record."""
    vehicle = get_vehicle_by_id(session, vehicle_id)
    if vehicle is None:
        raise VehicleNotFoundError(f"Vehicle {vehicle_id} was not found")

    latest_service = get_latest_scheduled_service(session, vehicle_id)
    if latest_service is None:
        raise ScheduledServiceNotFoundError(
            f"Vehicle {vehicle_id} has no scheduled service record"
        )

    months_since_last_service = _completed_months_between(
        latest_service.service_date,
        evaluation_date,
    )
    return evaluate_maintenance_due_status(
        current_odometer_km=vehicle.current_odometer_km,
        last_service_odometer_km=latest_service.odometer_km,
        months_since_last_service=months_since_last_service,
        service_interval_km=vehicle.service_interval_km,
        service_interval_months=vehicle.service_interval_months,
        due_soon_threshold_percent=due_soon_threshold_percent,
    )
