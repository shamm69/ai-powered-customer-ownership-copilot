"""Tests for deterministic scheduled-maintenance evaluation."""

import pytest

from app.maintenance import (
    MaintenanceDueResult,
    MaintenanceStatus,
    evaluate_maintenance_due_status,
)


def evaluate_with_defaults(**overrides: float) -> MaintenanceDueResult:
    inputs = {
        "current_odometer_km": 14_000,
        "last_service_odometer_km": 10_000,
        "months_since_last_service": 4,
        "service_interval_km": 10_000,
        "service_interval_months": 12,
        "due_soon_threshold_percent": 80,
    }
    inputs.update(overrides)
    return evaluate_maintenance_due_status(**inputs)


def test_service_not_due() -> None:
    result = evaluate_with_defaults()

    assert result.status is MaintenanceStatus.NOT_DUE
    assert result.kilometres_travelled_since_last_service == 4_000
    assert result.kilometres_remaining == 6_000
    assert result.months_remaining == 8
    assert "Neither distance nor time" in result.reasons[0]


def test_service_due_soon_by_distance() -> None:
    result = evaluate_with_defaults(current_odometer_km=18_500)

    assert result.status is MaintenanceStatus.DUE_SOON
    assert result.reasons == (
        "Distance caused due_soon status: the distance due-soon threshold has been "
        "reached or exceeded.",
    )


def test_service_due_soon_by_time() -> None:
    result = evaluate_with_defaults(months_since_last_service=10)

    assert result.status is MaintenanceStatus.DUE_SOON
    assert result.reasons == (
        "Time caused due_soon status: the time due-soon threshold has been reached "
        "or exceeded.",
    )


def test_service_overdue_by_distance() -> None:
    result = evaluate_with_defaults(current_odometer_km=20_500)

    assert result.status is MaintenanceStatus.OVERDUE
    assert result.kilometres_remaining == -500
    assert result.reasons == (
        "Distance caused overdue status: the distance service interval has been "
        "reached or exceeded.",
    )


def test_service_overdue_by_time() -> None:
    result = evaluate_with_defaults(months_since_last_service=13)

    assert result.status is MaintenanceStatus.OVERDUE
    assert result.months_remaining == -1
    assert result.reasons == (
        "Time caused overdue status: the time service interval has been reached or "
        "exceeded.",
    )


def test_service_overdue_when_both_limits_are_exceeded() -> None:
    result = evaluate_with_defaults(
        current_odometer_km=21_000,
        months_since_last_service=14,
    )

    assert result.status is MaintenanceStatus.OVERDUE
    assert len(result.reasons) == 2
    assert result.reasons[0].startswith("Distance caused overdue status")
    assert result.reasons[1].startswith("Time caused overdue status")


def test_current_odometer_cannot_be_lower_than_last_service_odometer() -> None:
    with pytest.raises(ValueError, match="must not be lower"):
        evaluate_with_defaults(
            current_odometer_km=9_999,
            last_service_odometer_km=10_000,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_odometer_km", -1),
        ("last_service_odometer_km", -1),
        ("months_since_last_service", -1),
        ("service_interval_km", -1),
        ("service_interval_months", -1),
        ("due_soon_threshold_percent", -1),
    ],
)
def test_negative_inputs_are_invalid(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        evaluate_with_defaults(**{field: value})


@pytest.mark.parametrize("threshold", [0, 100])
def test_due_soon_threshold_excludes_status_boundaries(threshold: float) -> None:
    with pytest.raises(ValueError, match="greater than 0 and less than 100"):
        evaluate_with_defaults(due_soon_threshold_percent=threshold)


def test_exact_due_soon_threshold_is_due_soon() -> None:
    result = evaluate_with_defaults(current_odometer_km=18_000)

    assert result.status is MaintenanceStatus.DUE_SOON
    assert result.reasons[0].startswith("Distance caused due_soon status")


def test_just_below_due_soon_threshold_is_not_due() -> None:
    result = evaluate_with_defaults(current_odometer_km=17_999)

    assert result.status is MaintenanceStatus.NOT_DUE


def test_full_interval_boundary_is_overdue() -> None:
    result = evaluate_with_defaults(current_odometer_km=20_000)

    assert result.status is MaintenanceStatus.OVERDUE
