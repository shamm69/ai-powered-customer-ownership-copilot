"""Tests for the deterministic synthetic seed operation."""

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Customer, ServiceRecord, Vehicle
from app.seed import seed_database


def create_test_session() -> Session:
    """Create a session backed by a fresh in-memory SQLite database."""
    test_engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    return Session(test_engine)


def test_seed_database_populates_expected_related_data() -> None:
    with create_test_session() as session:
        assert seed_database(session) is True

        customers = session.scalars(select(Customer).order_by(Customer.id)).all()
        vehicles = session.scalars(select(Vehicle).order_by(Vehicle.id)).all()
        service_records = session.scalars(
            select(ServiceRecord).order_by(ServiceRecord.id)
        ).all()

        assert len(customers) == 3
        assert len(vehicles) == 4
        assert len(service_records) == 7
        assert sum(len(customer.vehicles) for customer in customers) == 4
        assert all(vehicle.customer in customers for vehicle in vehicles)
        assert all(vehicle.service_records for vehicle in vehicles)
        assert all(record.vehicle in vehicles for record in service_records)

        vehicles_by_model = {vehicle.model: vehicle for vehicle in vehicles}
        assert (
            vehicles_by_model["Comet"].current_odometer_km
            - max(
                record.odometer_km
                for record in vehicles_by_model["Comet"].service_records
            )
            < vehicles_by_model["Comet"].service_interval_km * 0.2
        )
        assert (
            vehicles_by_model["Ridge"].current_odometer_km
            - max(
                record.odometer_km
                for record in vehicles_by_model["Ridge"].service_records
            )
            >= vehicles_by_model["Ridge"].service_interval_km * 0.8
        )
        assert (
            vehicles_by_model["Voyager"].current_odometer_km
            - max(
                record.odometer_km
                for record in vehicles_by_model["Voyager"].service_records
            )
            > vehicles_by_model["Voyager"].service_interval_km
        )


def test_seed_database_does_not_create_duplicates() -> None:
    with create_test_session() as session:
        assert seed_database(session) is True
        assert seed_database(session) is False

        assert session.scalar(select(func.count()).select_from(Customer)) == 3
        assert session.scalar(select(func.count()).select_from(Vehicle)) == 4
        assert session.scalar(select(func.count()).select_from(ServiceRecord)) == 7
