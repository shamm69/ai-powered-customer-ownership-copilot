"""Tests for the FastAPI application foundation."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def maintenance_payload(**overrides: float) -> dict[str, float]:
    payload = {
        "current_odometer_km": 14_000,
        "last_service_odometer_km": 10_000,
        "months_since_last_service": 4,
        "service_interval_km": 10_000,
        "service_interval_months": 12,
        "due_soon_threshold_percent": 80,
    }
    payload.update(overrides)
    return payload


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_evaluate_maintenance_not_due_response() -> None:
    response = client.post("/maintenance/evaluate", json=maintenance_payload())

    assert response.status_code == 200
    assert response.json() == {
        "status": "not_due",
        "kilometres_travelled_since_last_service": 4_000,
        "kilometres_remaining": 6_000,
        "months_remaining": 8,
        "reasons": [
            "Neither distance nor time caused a due status: both remain below the "
            "due-soon threshold."
        ],
    }


def test_evaluate_maintenance_due_soon() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(current_odometer_km=18_000),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "due_soon"


def test_evaluate_maintenance_overdue() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(months_since_last_service=13),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "overdue"


def test_evaluate_maintenance_rejects_negative_input() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(months_since_last_service=-1),
    )

    assert response.status_code == 422


def test_evaluate_maintenance_rejects_reversed_odometers() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(
            current_odometer_km=9_000,
            last_service_odometer_km=10_000,
        ),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "current_odometer_km must not be lower than last_service_odometer_km"
        )
    }


def test_evaluate_maintenance_rejects_invalid_service_interval() -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(service_interval_km=0),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("threshold", [0, 100])
def test_evaluate_maintenance_rejects_invalid_threshold(threshold: float) -> None:
    response = client.post(
        "/maintenance/evaluate",
        json=maintenance_payload(due_soon_threshold_percent=threshold),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "non_finite_value",
    [float("nan"), float("inf"), -float("inf")],
)
def test_evaluate_maintenance_rejects_non_finite_values(
    non_finite_value: float,
) -> None:
    payload = maintenance_payload(current_odometer_km=non_finite_value)

    response = client.post(
        "/maintenance/evaluate",
        content=json.dumps(payload),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
