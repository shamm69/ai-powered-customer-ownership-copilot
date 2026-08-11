"""Tests for evaluating maintenance from stored vehicle data."""

from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.maintenance import MaintenanceStatus, evaluate_maintenance_due_status
from app.maintenance_service import (
    MaintenanceServiceError,
    evaluate_vehicle_maintenance,
)
from app.models import Customer, ServiceRecord, Vehicle
from app.seed import seed_database


def create_test_session() -> Session:
    """Create a session backed by a fresh in-memory SQLite database."""
    test_engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    return Session(test_engine)


def add_vehicle(
    session: Session,
    *,
    current_odometer_km: float = 18_000,
    service_interval_km: float = 10_000,
    service_interval_months: float = 12,
) -> Vehicle:
    """Persist a synthetic vehicle for an integration test."""
    vehicle = Vehicle(
        customer=Customer(name="Taylor Morgan"),
        manufacturer="Aster Motors",
        model="Comet",
        model_year=2023,
        current_odometer_km=current_odometer_km,
        service_interval_km=service_interval_km,
        service_interval_months=service_interval_months,
    )
    session.add(vehicle)
    session.commit()
    return vehicle


def add_service_record(
    session: Session,
    vehicle: Vehicle,
    *,
    service_date: date,
    odometer_km: float,
    service_type: str = "scheduled",
) -> ServiceRecord:
    """Persist a synthetic service record for an integration test."""
    record = ServiceRecord(
        vehicle=vehicle,
        service_date=service_date,
        odometer_km=odometer_km,
        service_type=service_type,
    )
    session.add(record)
    session.commit()
    return record


def test_stored_data_matches_direct_domain_evaluation() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(session)
        add_service_record(
            session,
            vehicle,
            service_date=date(2026, 1, 15),
            odometer_km=10_000,
        )

        result = evaluate_vehicle_maintenance(
            session,
            vehicle.id,
            evaluation_date=date(2026, 4, 15),
        )
        expected = evaluate_maintenance_due_status(
            current_odometer_km=18_000,
            last_service_odometer_km=10_000,
            months_since_last_service=3,
            service_interval_km=10_000,
            service_interval_months=12,
            due_soon_threshold_percent=80,
        )

        assert result == expected


def test_missing_vehicle_raises_clear_error() -> None:
    with create_test_session() as session:
        with pytest.raises(MaintenanceServiceError, match="Vehicle 999 was not found"):
            evaluate_vehicle_maintenance(
                session,
                999,
                evaluation_date=date(2026, 4, 15),
            )


def test_vehicle_without_scheduled_service_raises_clear_error() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(session)

        with pytest.raises(
            MaintenanceServiceError,
            match="has no scheduled service record",
        ):
            evaluate_vehicle_maintenance(
                session,
                vehicle.id,
                evaluation_date=date(2026, 4, 15),
            )


def test_stored_values_and_completed_months_are_passed_to_domain() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(
            session,
            current_odometer_km=24_500,
            service_interval_km=12_000,
            service_interval_months=18,
        )
        add_service_record(
            session,
            vehicle,
            service_date=date(2026, 1, 15),
            odometer_km=16_000,
        )

        with patch(
            "app.maintenance_service.evaluate_maintenance_due_status"
        ) as evaluator:
            evaluate_vehicle_maintenance(
                session,
                vehicle.id,
                evaluation_date=date(2026, 4, 14),
            )

        evaluator.assert_called_once_with(
            current_odometer_km=24_500,
            last_service_odometer_km=16_000,
            months_since_last_service=2,
            service_interval_km=12_000,
            service_interval_months=18,
            due_soon_threshold_percent=80.0,
        )


def test_seeded_vehicle_can_be_evaluated() -> None:
    with create_test_session() as session:
        seed_database(session)
        vehicle = session.scalar(select(Vehicle).where(Vehicle.model == "Ridge"))
        assert vehicle is not None

        result = evaluate_vehicle_maintenance(
            session,
            vehicle.id,
            evaluation_date=date(2026, 8, 11),
        )

        assert result.status is MaintenanceStatus.DUE_SOON


def test_non_scheduled_record_does_not_replace_latest_scheduled_service() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(session, current_odometer_km=20_000)
        add_service_record(
            session,
            vehicle,
            service_date=date(2025, 1, 15),
            odometer_km=10_000,
        )
        add_service_record(
            session,
            vehicle,
            service_date=date(2026, 1, 15),
            odometer_km=19_500,
            service_type="repair",
        )

        result = evaluate_vehicle_maintenance(
            session,
            vehicle.id,
            evaluation_date=date(2026, 4, 15),
        )

        assert result.status is MaintenanceStatus.OVERDUE
        assert result.kilometres_travelled_since_last_service == 10_000


def test_evaluation_date_before_service_date_raises_clear_error() -> None:
    with create_test_session() as session:
        vehicle = add_vehicle(session)
        add_service_record(
            session,
            vehicle,
            service_date=date(2026, 4, 15),
            odometer_km=10_000,
        )

        with pytest.raises(MaintenanceServiceError, match="must not be earlier"):
            evaluate_vehicle_maintenance(
                session,
                vehicle.id,
                evaluation_date=date(2026, 4, 14),
            )
