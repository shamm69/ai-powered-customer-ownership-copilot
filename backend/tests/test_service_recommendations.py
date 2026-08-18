"""Tests for deterministic stored-vehicle service recommendations."""

from dataclasses import FrozenInstanceError
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.maintenance import MaintenanceDueResult, MaintenanceStatus
from app.service_recommendations import (
    RecommendationContext,
    RecommendationPriority,
    ServiceRecommendationResult,
    ServiceType,
    recommend_vehicle_services,
)
from app.seed import seed_database


def maintenance_result(
    status: MaintenanceStatus,
    distance_since_service: float = 2_000.0,
) -> MaintenanceDueResult:
    return MaintenanceDueResult(
        status=status,
        kilometres_travelled_since_last_service=distance_since_service,
        kilometres_remaining=10_000.0 - distance_since_service,
        months_remaining=6.0,
        reasons=(f"Authoritative status: {status.value}.",),
    )


def recommend(
    monkeypatch: MonkeyPatch,
    status: MaintenanceStatus = MaintenanceStatus.NOT_DUE,
    *,
    distance_since_service: float = 2_000.0,
    model_year: int = 2023,
    context: RecommendationContext = RecommendationContext.GENERAL,
) -> ServiceRecommendationResult:
    result = maintenance_result(status, distance_since_service)
    monkeypatch.setattr(
        "app.service_recommendations.evaluate_vehicle_maintenance",
        lambda **_: result,
    )
    monkeypatch.setattr(
        "app.service_recommendations.get_vehicle_by_id",
        lambda *_: SimpleNamespace(model_year=model_year),
    )
    return recommend_vehicle_services(
        session=MagicMock(spec=Session),
        vehicle_id=1,
        evaluation_date=date(2026, 8, 18),
        recommendation_context=context,
    )


def test_overdue_recommends_urgent_periodic_maintenance(
    monkeypatch: MonkeyPatch,
) -> None:
    result = recommend(monkeypatch, MaintenanceStatus.OVERDUE)

    recommendation = result.recommendations[0]
    assert recommendation.service_type is ServiceType.PERIODIC_MAINTENANCE
    assert recommendation.priority is RecommendationPriority.URGENT
    assert recommendation.supporting_factors == result.maintenance_result.reasons


def test_due_soon_recommends_periodic_maintenance(
    monkeypatch: MonkeyPatch,
) -> None:
    result = recommend(monkeypatch, MaintenanceStatus.DUE_SOON)

    assert result.recommendations[0].service_type is ServiceType.PERIODIC_MAINTENANCE
    assert result.recommendations[0].priority is RecommendationPriority.DUE_SOON


def test_not_due_does_not_invent_scheduled_service(
    monkeypatch: MonkeyPatch,
) -> None:
    result = recommend(monkeypatch)

    assert result.recommendations[0].service_type is ServiceType.NO_SERVICE_REQUIRED
    assert all(
        item.service_type is not ServiceType.PERIODIC_MAINTENANCE
        for item in result.recommendations
    )


def test_long_trip_adds_preventive_inspection_without_fault_claim(
    monkeypatch: MonkeyPatch,
) -> None:
    result = recommend(monkeypatch, context=RecommendationContext.LONG_TRIP)

    recommendation = result.recommendations[0]
    assert recommendation.service_type is ServiceType.PRE_TRIP_INSPECTION
    assert recommendation.priority is RecommendationPriority.RECOMMENDED
    assert "does not indicate a fault" in recommendation.reason


def test_distance_rule_adds_tyre_inspection(
    monkeypatch: MonkeyPatch,
) -> None:
    result = recommend(monkeypatch, distance_since_service=8_000.0)

    assert [item.service_type for item in result.recommendations] == [
        ServiceType.TYRE_INSPECTION_ROTATION,
    ]
    assert "8000 km" in result.recommendations[0].supporting_factors[0]


def test_age_rule_adds_battery_health_check(
    monkeypatch: MonkeyPatch,
) -> None:
    result = recommend(monkeypatch, model_year=2021)

    assert result.recommendations[0].service_type is ServiceType.BATTERY_HEALTH_CHECK
    assert "not a battery-failure diagnosis" in result.recommendations[0].reason


def test_multiple_recommendations_have_deterministic_order(
    monkeypatch: MonkeyPatch,
) -> None:
    result = recommend(
        monkeypatch,
        MaintenanceStatus.OVERDUE,
        distance_since_service=9_000.0,
        model_year=2020,
        context=RecommendationContext.LONG_TRIP,
    )

    assert [item.service_type for item in result.recommendations] == [
        ServiceType.PERIODIC_MAINTENANCE,
        ServiceType.PRE_TRIP_INSPECTION,
        ServiceType.TYRE_INSPECTION_ROTATION,
        ServiceType.BATTERY_HEALTH_CHECK,
    ]


def test_result_is_immutable(monkeypatch: MonkeyPatch) -> None:
    result = recommend(monkeypatch)

    with pytest.raises(FrozenInstanceError):
        result.recommendations = ()  # type: ignore[misc]


def test_seeded_vehicle_supports_real_pre_trip_recommendation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "demo.db"
    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        seed_database(session)
        result = recommend_vehicle_services(
            session=session,
            vehicle_id=1,
            evaluation_date=date(2026, 8, 18),
            recommendation_context=RecommendationContext.LONG_TRIP,
        )

    assert result.maintenance_result.status is MaintenanceStatus.NOT_DUE
    assert [item.service_type for item in result.recommendations] == [
        ServiceType.PRE_TRIP_INSPECTION,
    ]
