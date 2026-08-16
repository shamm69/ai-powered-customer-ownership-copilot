"""Deterministic synthetic snapshots for predictive-maintenance experiments."""

from dataclasses import dataclass
from math import exp, isfinite
from random import Random

DEFAULT_SNAPSHOT_COUNT = 1_500
DEFAULT_RANDOM_SEED = 20_260_817

PREDICTIVE_MAINTENANCE_FEATURE_NAMES: tuple[str, ...] = (
    "vehicle_age_years",
    "current_odometer_km",
    "distance_since_last_scheduled_service_km",
    "months_since_last_scheduled_service",
    "service_interval_km",
    "service_interval_months",
    "average_monthly_driving_km",
    "usage_severity_score",
)

_SERVICE_INTERVALS = (
    (10_000.0, 12.0),
    (15_000.0, 12.0),
    (15_000.0, 18.0),
    (20_000.0, 24.0),
)


@dataclass(frozen=True)
class PredictiveMaintenanceSnapshot:
    """One vehicle snapshot and its independently simulated future outcome."""

    synthetic_vehicle_id: int
    vehicle_age_years: float
    current_odometer_km: float
    distance_since_last_scheduled_service_km: float
    months_since_last_scheduled_service: float
    service_interval_km: float
    service_interval_months: float
    average_monthly_driving_km: float
    usage_severity_score: float
    maintenance_needed_within_90_days: int

    def __post_init__(self) -> None:
        if self.synthetic_vehicle_id <= 0:
            raise ValueError("synthetic_vehicle_id must be positive")

        numeric_values = {
            "vehicle_age_years": self.vehicle_age_years,
            "current_odometer_km": self.current_odometer_km,
            "distance_since_last_scheduled_service_km": (
                self.distance_since_last_scheduled_service_km
            ),
            "months_since_last_scheduled_service": (
                self.months_since_last_scheduled_service
            ),
            "service_interval_km": self.service_interval_km,
            "service_interval_months": self.service_interval_months,
            "average_monthly_driving_km": self.average_monthly_driving_km,
            "usage_severity_score": self.usage_severity_score,
        }
        if not all(isfinite(value) for value in numeric_values.values()):
            raise ValueError("snapshot numeric values must be finite")
        if self.vehicle_age_years <= 0:
            raise ValueError("vehicle_age_years must be positive")
        if self.current_odometer_km < 0:
            raise ValueError("current_odometer_km must not be negative")
        if self.distance_since_last_scheduled_service_km < 0:
            raise ValueError(
                "distance_since_last_scheduled_service_km must not be negative"
            )
        if (
            self.distance_since_last_scheduled_service_km
            > self.current_odometer_km
        ):
            raise ValueError(
                "distance since service must not exceed current odometer"
            )
        if self.months_since_last_scheduled_service < 0:
            raise ValueError(
                "months_since_last_scheduled_service must not be negative"
            )
        if self.service_interval_km <= 0 or self.service_interval_months <= 0:
            raise ValueError("service intervals must be positive")
        if self.average_monthly_driving_km <= 0:
            raise ValueError("average_monthly_driving_km must be positive")
        if not 0.0 <= self.usage_severity_score <= 1.0:
            raise ValueError("usage_severity_score must be between 0 and 1")
        if self.maintenance_needed_within_90_days not in (0, 1):
            raise ValueError("maintenance_needed_within_90_days must be binary")


def extract_predictive_maintenance_features(
    snapshot: PredictiveMaintenanceSnapshot,
) -> tuple[float, ...]:
    """Return only the ordered values permitted as later model inputs."""
    return (
        snapshot.vehicle_age_years,
        snapshot.current_odometer_km,
        snapshot.distance_since_last_scheduled_service_km,
        snapshot.months_since_last_scheduled_service,
        snapshot.service_interval_km,
        snapshot.service_interval_months,
        snapshot.average_monthly_driving_km,
        snapshot.usage_severity_score,
    )


def generate_predictive_maintenance_snapshots(
    row_count: int = DEFAULT_SNAPSHOT_COUNT,
    seed: int = DEFAULT_RANDOM_SEED,
) -> tuple[PredictiveMaintenanceSnapshot, ...]:
    """Generate independent, reproducible synthetic vehicle snapshots."""
    if (
        isinstance(row_count, bool)
        or not isinstance(row_count, int)
        or row_count <= 0
    ):
        raise ValueError("row_count must be a positive integer")

    random = Random(seed)
    snapshots: list[PredictiveMaintenanceSnapshot] = []

    for synthetic_vehicle_id in range(1, row_count + 1):
        vehicle_age_years = float(random.randint(1, 18))
        average_monthly_driving_km = round(
            max(200.0, min(3_500.0, random.gauss(1_200.0, 500.0))),
            2,
        )
        usage_severity_score = round(random.betavariate(2.0, 2.0), 4)
        service_interval_km, service_interval_months = random.choice(
            _SERVICE_INTERVALS
        )

        service_progress = random.betavariate(1.7, 1.7) * 1.35
        months_since_last_service = round(
            service_interval_months * service_progress,
            2,
        )
        distance_since_last_service = round(
            average_monthly_driving_km
            * months_since_last_service
            * random.uniform(0.75, 1.25),
            2,
        )
        estimated_lifetime_distance = round(
            average_monthly_driving_km
            * vehicle_age_years
            * 12.0
            * random.uniform(0.75, 1.25),
            2,
        )
        current_odometer_km = max(
            distance_since_last_service,
            estimated_lifetime_distance,
        )

        target = _simulate_future_maintenance_need(
            random=random,
            vehicle_age_years=vehicle_age_years,
            distance_since_last_service_km=distance_since_last_service,
            months_since_last_service=months_since_last_service,
            service_interval_km=service_interval_km,
            service_interval_months=service_interval_months,
            average_monthly_driving_km=average_monthly_driving_km,
            usage_severity_score=usage_severity_score,
        )
        snapshots.append(
            PredictiveMaintenanceSnapshot(
                synthetic_vehicle_id=synthetic_vehicle_id,
                vehicle_age_years=vehicle_age_years,
                current_odometer_km=current_odometer_km,
                distance_since_last_scheduled_service_km=(
                    distance_since_last_service
                ),
                months_since_last_scheduled_service=months_since_last_service,
                service_interval_km=service_interval_km,
                service_interval_months=service_interval_months,
                average_monthly_driving_km=average_monthly_driving_km,
                usage_severity_score=usage_severity_score,
                maintenance_needed_within_90_days=target,
            )
        )

    return tuple(snapshots)


def _simulate_future_maintenance_need(
    *,
    random: Random,
    vehicle_age_years: float,
    distance_since_last_service_km: float,
    months_since_last_service: float,
    service_interval_km: float,
    service_interval_months: float,
    average_monthly_driving_km: float,
    usage_severity_score: float,
) -> int:
    """Simulate a noisy 90-day future outcome without using baseline status."""
    future_driving_variation = max(0.4, random.gauss(1.0, 0.2))
    future_distance_km = (
        average_monthly_driving_km * 3.0 * future_driving_variation
    )
    projected_distance_ratio = (
        distance_since_last_service_km + future_distance_km
    ) / service_interval_km
    projected_time_ratio = (
        months_since_last_service + 3.0
    ) / service_interval_months

    latent_score = (
        -1.35
        + 1.25 * (projected_distance_ratio - 0.8)
        + 1.35 * (projected_time_ratio - 0.8)
        + 1.10 * (usage_severity_score - 0.5)
        + 0.55 * ((vehicle_age_years - 8.0) / 8.0)
        + 0.35 * ((average_monthly_driving_km - 1_200.0) / 800.0)
        + random.gauss(0.0, 0.75)
    )
    probability = 1.0 / (1.0 + exp(-latent_score))
    return int(random.random() < probability)
