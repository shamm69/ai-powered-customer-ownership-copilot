"""SQLAlchemy models for customers, vehicles, and service history."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Customer(Base):
    """A customer who can own one or more vehicles."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    vehicles: Mapped[list[Vehicle]] = relationship(back_populates="customer")


class Vehicle(Base):
    """A vehicle owned by a customer."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
    )
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    model_year: Mapped[int] = mapped_column(nullable=False)
    current_odometer_km: Mapped[float] = mapped_column(Float, nullable=False)
    service_interval_km: Mapped[float] = mapped_column(Float, nullable=False)
    service_interval_months: Mapped[float] = mapped_column(Float, nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="vehicles")
    service_records: Mapped[list[ServiceRecord]] = relationship(
        back_populates="vehicle"
    )


class ServiceRecord(Base):
    """A completed service event for a vehicle."""

    __tablename__ = "service_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id"),
        nullable=False,
    )
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    odometer_km: Mapped[float] = mapped_column(Float, nullable=False)
    service_type: Mapped[str] = mapped_column(String(100), nullable=False)

    vehicle: Mapped[Vehicle] = relationship(back_populates="service_records")
