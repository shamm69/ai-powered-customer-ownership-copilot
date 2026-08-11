"""Small, explicit queries for vehicle maintenance data."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ServiceRecord, Vehicle


def get_vehicle_by_id(session: Session, vehicle_id: int) -> Vehicle | None:
    """Return a vehicle by primary key, or None when it does not exist."""
    return session.get(Vehicle, vehicle_id)


def get_latest_scheduled_service(
    session: Session,
    vehicle_id: int,
) -> ServiceRecord | None:
    """Return a vehicle's latest scheduled service, or None when absent."""
    statement = (
        select(ServiceRecord)
        .where(
            ServiceRecord.vehicle_id == vehicle_id,
            ServiceRecord.service_type == "scheduled",
        )
        .order_by(ServiceRecord.service_date.desc(), ServiceRecord.id.desc())
        .limit(1)
    )
    return session.scalar(statement)
