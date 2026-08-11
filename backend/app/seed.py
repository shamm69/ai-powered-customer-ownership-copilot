"""Deterministic synthetic data for local development and demonstrations."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Customer, ServiceRecord, Vehicle


def _build_synthetic_customers() -> list[Customer]:
    """Build a small, readable customer and vehicle dataset."""
    return [
        Customer(
            name="Avery Singh",
            vehicles=[
                Vehicle(
                    manufacturer="Aster Motors",
                    model="Comet",
                    model_year=2023,
                    current_odometer_km=12_500,
                    service_interval_km=10_000,
                    service_interval_months=12,
                    service_records=[
                        ServiceRecord(
                            service_date=date(2025, 7, 15),
                            odometer_km=2_000,
                            service_type="Initial inspection",
                        ),
                        ServiceRecord(
                            service_date=date(2026, 7, 15),
                            odometer_km=12_000,
                            service_type="Scheduled maintenance",
                        ),
                    ],
                ),
                Vehicle(
                    manufacturer="Summit Automotive",
                    model="Ridge",
                    model_year=2021,
                    current_odometer_km=30_000,
                    service_interval_km=10_000,
                    service_interval_months=12,
                    service_records=[
                        ServiceRecord(
                            service_date=date(2024, 12, 5),
                            odometer_km=10_000,
                            service_type="Scheduled maintenance",
                        ),
                        ServiceRecord(
                            service_date=date(2025, 12, 5),
                            odometer_km=21_500,
                            service_type="Scheduled maintenance",
                        ),
                    ],
                ),
            ],
        ),
        Customer(
            name="Jordan Lee",
            vehicles=[
                Vehicle(
                    manufacturer="Harbor Mobility",
                    model="Voyager",
                    model_year=2020,
                    current_odometer_km=52_000,
                    service_interval_km=10_000,
                    service_interval_months=10,
                    service_records=[
                        ServiceRecord(
                            service_date=date(2024, 4, 20),
                            odometer_km=20_000,
                            service_type="Scheduled maintenance",
                        ),
                        ServiceRecord(
                            service_date=date(2025, 4, 20),
                            odometer_km=40_000,
                            service_type="Major service",
                        ),
                    ],
                )
            ],
        ),
        Customer(
            name="Samira Patel",
            vehicles=[
                Vehicle(
                    manufacturer="Aster Motors",
                    model="Lumen",
                    model_year=2024,
                    current_odometer_km=9_000,
                    service_interval_km=15_000,
                    service_interval_months=18,
                    service_records=[
                        ServiceRecord(
                            service_date=date(2026, 5, 10),
                            odometer_km=7_500,
                            service_type="Routine inspection",
                        )
                    ],
                )
            ],
        ),
    ]


def seed_database(session: Session) -> bool:
    """Seed an empty database once and report whether data was added."""
    if session.scalar(select(Customer.id).limit(1)) is not None:
        return False

    session.add_all(_build_synthetic_customers())
    session.commit()
    return True


def main() -> None:
    """Create development tables and add synthetic data when they are empty."""
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seeded = seed_database(session)

    if seeded:
        print("Synthetic seed data added.")
    else:
        print("Database already contains customers; no seed data added.")


if __name__ == "__main__":
    main()
