"""Application entry point for the Customer Ownership Copilot API."""

from datetime import date
from functools import lru_cache
from math import isfinite
import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.orm import Session

from app.database import get_db
from app.document_embeddings import SentenceTransformerEmbedder
from app.gemini_answer_generator import (
    GeminiAnswerGenerator,
    GeminiConfigurationError,
    GeminiGenerationError,
)
from app.grounded_answers import AnswerSource, GroundedAnswer
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
from app.rag_service import RagService, prepare_rag_service
from app.retrieval_confidence import RetrievalSupportStatus

RAG_TOP_K_ENVIRONMENT_VARIABLE = "RAG_TOP_K"
RAG_MINIMUM_SIMILARITY_ENVIRONMENT_VARIABLE = "RAG_MINIMUM_SIMILARITY"
DEFAULT_RAG_TOP_K = 3
DEFAULT_RAG_MINIMUM_SIMILARITY = 0.5


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


class SupportQueryRequest(BaseModel):
    """A support question to answer from the controlled knowledge corpus."""

    question: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ]


class SupportSourceResponse(BaseModel):
    """Source metadata supporting a grounded API answer."""

    source_id: str
    document_title: str
    section_title: str
    chunk_id: str


class SupportQueryResponse(BaseModel):
    """Typed API representation of a grounded support answer."""

    answer: str
    retrieval_status: RetrievalSupportStatus
    sources: list[SupportSourceResponse]


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


def support_response(answer: GroundedAnswer) -> SupportQueryResponse:
    """Map a grounded answer to the typed support API response."""
    return SupportQueryResponse(
        answer=answer.answer,
        retrieval_status=answer.retrieval_status,
        sources=[support_source_response(source) for source in answer.sources],
    )


def support_source_response(source: AnswerSource) -> SupportSourceResponse:
    """Map one approved answer source to its API representation."""
    return SupportSourceResponse(
        source_id=source.source_id,
        document_title=source.document_title,
        section_title=source.section_title,
        chunk_id=source.chunk_id,
    )


@lru_cache(maxsize=1)
def build_rag_service() -> RagService:
    """Prepare and cache the runtime RAG service on first use."""
    top_k = _positive_integer_environment_value(
        RAG_TOP_K_ENVIRONMENT_VARIABLE,
        DEFAULT_RAG_TOP_K,
    )
    minimum_similarity = _similarity_environment_value(
        RAG_MINIMUM_SIMILARITY_ENVIRONMENT_VARIABLE,
        DEFAULT_RAG_MINIMUM_SIMILARITY,
    )
    return prepare_rag_service(
        SentenceTransformerEmbedder(),
        GeminiAnswerGenerator(),
        top_k=top_k,
        minimum_similarity=minimum_similarity,
    )


def get_rag_service() -> RagService:
    """Provide the prepared service and translate preparation failures."""
    try:
        return build_rag_service()
    except GeminiConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Support answer service is not configured",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Support answer service could not be prepared",
        ) from exc


def _positive_integer_environment_value(name: str, default: int) -> int:
    configured_value = os.getenv(name, str(default))
    try:
        value = int(configured_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _similarity_environment_value(name: str, default: float) -> float:
    configured_value = os.getenv(name, str(default))
    try:
        value = float(configured_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be between -1.0 and 1.0") from exc
    if not isfinite(value) or not -1.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between -1.0 and 1.0")
    return value

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
    "/support/query",
    response_model=SupportQueryResponse,
    tags=["support"],
)
def query_support_documents(
    request: SupportQueryRequest,
    rag_service: RagService = Depends(get_rag_service),
) -> SupportQueryResponse:
    """Answer a question using the prepared grounded-support pipeline."""
    try:
        answer = rag_service.answer_question(request.question)
    except GeminiConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Support answer service is not configured",
        ) from exc
    except GeminiGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Support answer provider could not generate a response",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Support query could not be completed",
        ) from exc

    return support_response(answer)


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
