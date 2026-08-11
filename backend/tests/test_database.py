"""Tests for the synthetic SQLite data-layer foundation."""

from datetime import date

from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Customer, ServiceRecord, Vehicle


def create_test_engine() -> Engine:
    """Create a fresh in-memory SQLite engine for one test."""
    return create_engine("sqlite+pysqlite:///:memory:")


def test_database_tables_can_be_created() -> None:
    test_engine = create_test_engine()

    Base.metadata.create_all(test_engine)

    assert set(inspect(test_engine).get_table_names()) == {
        "customers",
        "service_records",
        "vehicles",
    }


def test_customer_vehicle_and_service_record_relationships() -> None:
    test_engine = create_test_engine()
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        customer = Customer(name="Avery Singh")
        vehicle = Vehicle(
            customer=customer,
            manufacturer="Aster Motors",
            model="Comet",
            model_year=2023,
            current_odometer_km=18_500,
            service_interval_km=10_000,
            service_interval_months=12,
        )
        service_record = ServiceRecord(
            vehicle=vehicle,
            service_date=date(2025, 8, 11),
            odometer_km=10_000,
            service_type="Scheduled maintenance",
        )
        session.add_all([customer, vehicle, service_record])
        session.commit()

        customer_id = customer.id
        vehicle_id = vehicle.id
        service_record_id = service_record.id
        session.expire_all()

        stored_customer = session.get(Customer, customer_id)
        stored_vehicle = session.get(Vehicle, vehicle_id)
        stored_service_record = session.get(ServiceRecord, service_record_id)

        assert stored_customer is not None
        assert stored_vehicle is not None
        assert stored_service_record is not None
        assert stored_customer.vehicles == [stored_vehicle]
        assert stored_vehicle.customer == stored_customer
        assert stored_vehicle.service_records == [stored_service_record]
        assert stored_service_record.vehicle == stored_vehicle
