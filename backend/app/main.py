"""Application entry point for the Customer Ownership Copilot API."""

from datetime import date
from math import isfinite

from fastapi import Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.maintenance import (
    MaintenanceDueResult,
    MaintenanceStatus,
    evaluate_maintenance_due_status,
)
from app.maintenance_service import (
    MaintenanceServiceError,
    ScheduledServiceNotFoundError,
    VehicleNotFoundError,
    evaluate_vehicle_maintenance,
)


class MaintenanceEvaluationRequest(BaseModel):
    """Inputs needed to evaluate a scheduled-service interval."""

    model_config = ConfigDict(allow_inf_nan=False)

    current_odometer_km: float = Field(ge=0)
    last_service_odometer_km: float = Field(ge=0)
    months_since_last_service: float = Field(ge=0)
    service_interval_km: float = Field(gt=0)
    service_interval_months: float = Field(gt=0)
    due_soon_threshold_percent: float = Field(gt=0, lt=100)


class MaintenanceEvaluationResponse(BaseModel):
    """Typed API representation of a maintenance due-status result."""

    status: MaintenanceStatus
    kilometres_travelled_since_last_service: float
    kilometres_remaining: float
    months_remaining: float
    reasons: list[str]


def get_evaluation_date() -> date:
    """Provide today's date at the HTTP boundary."""
    return date.today()


def maintenance_response(
    result: MaintenanceDueResult,
) -> MaintenanceEvaluationResponse:
    """Map a domain result to the shared API response model."""
    return MaintenanceEvaluationResponse(
        status=result.status,
        kilometres_travelled_since_last_service=(
            result.kilometres_travelled_since_last_service
        ),
        kilometres_remaining=result.kilometres_remaining,
        months_remaining=result.months_remaining,
        reasons=list(result.reasons),
    )

app = FastAPI(
    title="Customer Ownership Copilot API",
    version="0.1.0",
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return serializable 422 details when an invalid input is non-finite."""
    errors = exc.errors()
    for error in errors:
        invalid_input = error.get("input")
        if isinstance(invalid_input, float) and not isfinite(invalid_input):
            error["input"] = str(invalid_input)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": errors},
    )


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Report whether the API process is ready to accept requests."""
    return {"status": "healthy"}


@app.post(
    "/maintenance/evaluate",
    response_model=MaintenanceEvaluationResponse,
    tags=["maintenance"],
)
def evaluate_maintenance(
    request: MaintenanceEvaluationRequest,
) -> MaintenanceEvaluationResponse:
    """Evaluate service urgency using the deterministic maintenance rule."""
    try:
        result = evaluate_maintenance_due_status(
            current_odometer_km=request.current_odometer_km,
            last_service_odometer_km=request.last_service_odometer_km,
            months_since_last_service=request.months_since_last_service,
            service_interval_km=request.service_interval_km,
            service_interval_months=request.service_interval_months,
            due_soon_threshold_percent=request.due_soon_threshold_percent,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return maintenance_response(result)


@app.get(
    "/vehicles/{vehicle_id}/maintenance",
    response_model=MaintenanceEvaluationResponse,
    tags=["maintenance"],
)
def get_vehicle_maintenance(
    vehicle_id: int = Path(gt=0),
    session: Session = Depends(get_db),
    evaluation_date: date = Depends(get_evaluation_date),
) -> MaintenanceEvaluationResponse:
    """Evaluate maintenance status using stored vehicle and service data."""
    try:
        result = evaluate_vehicle_maintenance(
            session=session,
            vehicle_id=vehicle_id,
            evaluation_date=evaluation_date,
        )
    except VehicleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        ) from exc
    except ScheduledServiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vehicle has no scheduled service record",
        ) from exc
    except MaintenanceServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Maintenance evaluation could not be completed",
        ) from exc

    return maintenance_response(result)
