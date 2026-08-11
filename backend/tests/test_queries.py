"""Tests for the minimal vehicle and service-record queries."""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Customer, ServiceRecord, Vehicle
from app.queries import get_latest_scheduled_service, get_vehicle_by_id


def create_test_session() -> Session:
    """Create a session backed by a fresh in-memory SQLite database."""
    test_engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    return Session(test_engine)


def add_vehicle(session: Session) -> Vehicle:
    """Persist a simple synthetic customer and vehicle for one test."""
    vehicle = Vehicle(
        customer=Customer(name="Taylor Morgan"),
        manufacturer="Aster Motors",
        model="Comet",
        model_year=2023,
        current_odometer_km=20_000,
        service_interval_km=10_000,
        service_interval_months=12,
    )
    session.add(vehicle)
    session.commit()
    return vehicle


def add_service_record(
    session: Session,
    vehicle: Vehicle,
    service_date: date,
    service_type: str,
) -> ServiceRecord:
    """Persist a synthetic service record for a test vehicle."""
    record = ServiceRecord(
        vehicle=vehicle,
        service_date=service_date,
        odometer_km=10_000,
        service_type=service_type,
    )
    session.add(record)
    session.commit()
    return record


def test_get_vehicle_by_id_returns_existing_vehicle() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(session)

        result = get_vehicle_by_id(session, vehicle.id)

        assert result == vehicle


def test_get_vehicle_by_id_returns_none_for_missing_vehicle() -> None:
    with create_test_session() as session:
        assert get_vehicle_by_id(session, 999) is None


def test_latest_scheduled_service_is_selected_by_date() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(session)
        add_service_record(session, vehicle, date(2025, 1, 15), "scheduled")
        latest = add_service_record(
            session,
            vehicle,
            date(2026, 1, 15),
            "scheduled",
        )

        result = get_latest_scheduled_service(session, vehicle.id)

        assert result == latest


def test_latest_scheduled_service_ignores_non_scheduled_records() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(session)
        scheduled = add_service_record(
            session,
            vehicle,
            date(2025, 1, 15),
            "scheduled",
        )
        add_service_record(session, vehicle, date(2026, 1, 15), "repair")

        result = get_latest_scheduled_service(session, vehicle.id)

        assert result == scheduled


def test_latest_scheduled_service_returns_none_when_absent() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(session)
        add_service_record(session, vehicle, date(2026, 1, 15), "inspection")

        assert get_latest_scheduled_service(session, vehicle.id) is None


def test_latest_scheduled_service_uses_highest_id_to_break_date_tie() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(session)
        shared_date = date(2026, 1, 15)
        first = add_service_record(session, vehicle, shared_date, "scheduled")
        second = add_service_record(session, vehicle, shared_date, "scheduled")

        result = get_latest_scheduled_service(session, vehicle.id)

        assert second.id > first.id
        assert result == second
