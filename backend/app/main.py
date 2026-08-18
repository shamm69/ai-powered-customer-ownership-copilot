"""Application entry point for the Customer Ownership Copilot API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
from app.escalation import (
    EscalationReason,
    HandoffStatus,
    HumanHandoffResult,
    create_human_handoff,
)
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
from app.orchestrator import (
    OrchestratedCapability,
    OrchestrationContext,
    OrchestrationContextField,
    OrchestrationOutcome,
    OrchestrationResult,
    orchestrate_user_request,
)
from app.predictive_maintenance_artifact import (
    ExperimentalArtifactCompatibilityError,
)
from app.predictive_maintenance_comparison import (
    MaintenancePredictionComparison,
    MaintenancePredictionComparisonService,
    MaintenanceSignalRelationship,
    load_default_maintenance_prediction_comparison_service,
)
from app.predictive_maintenance_prediction import (
    ExperimentalMaintenancePredictionError,
    PredictiveMaintenanceFeatureInput,
)
from app.rag_service import RagService, prepare_rag_service
from app.retrieval_confidence import RetrievalSupportStatus
from app.routing import RoutingDecision, RoutingIntent
from app.runtime_bootstrap import initialize_runtime
from app.runtime_configuration import (
    configure_cors,
    get_predictive_artifact_directory,
)

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


class PredictiveMaintenanceComparisonRequest(BaseModel):
    """Eight public runtime features for the experimental comparison."""

    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

    vehicle_age_years: float = Field(gt=0)
    current_odometer_km: float = Field(ge=0)
    distance_since_last_scheduled_service_km: float = Field(ge=0)
    months_since_last_scheduled_service: float = Field(ge=0)
    service_interval_km: float = Field(gt=0)
    service_interval_months: float = Field(gt=0)
    average_monthly_driving_km: float = Field(gt=0)
    usage_severity_score: float = Field(ge=0, le=1)


class ExperimentalMaintenanceResponse(BaseModel):
    """Typed API representation of the non-authoritative ML signal."""

    maintenance_needed_within_90_days_prediction: int
    positive_class_probability: float
    threshold: float
    experimental: bool
    artifact_schema_version: int


class MaintenanceComparisonSignalsResponse(BaseModel):
    """Binary relationship metadata that does not merge either result."""

    deterministic_binary_signal: int
    experimental_ml_binary_signal: int
    relationship: MaintenanceSignalRelationship


class PredictiveMaintenanceComparisonResponse(BaseModel):
    """Separate authoritative deterministic and experimental ML results."""

    deterministic: MaintenanceEvaluationResponse
    experimental_ml: ExperimentalMaintenanceResponse
    comparison: MaintenanceComparisonSignalsResponse


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


class AssistantQueryRequest(BaseModel):
    """User message plus optional route-specific client context."""

    model_config = ConfigDict(extra="forbid")

    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ]
    vehicle_id: int | None = Field(default=None, gt=0)
    evaluation_date: date | None = None
    predictive_maintenance_input: (
        PredictiveMaintenanceComparisonRequest | None
    ) = None


class RoutingDecisionResponse(BaseModel):
    """Typed API representation of the deterministic routing decision."""

    intent: RoutingIntent
    normalized_request: str
    matched_intents: list[RoutingIntent]
    reason: str


class HumanHandoffResponse(BaseModel):
    """Typed API representation of the mock escalation result."""

    ticket_id: str
    reason: EscalationReason
    request_summary: str
    status: HandoffStatus


class AssistantQueryResponse(BaseModel):
    """Structured orchestration response with capability-specific results."""

    routing_decision: RoutingDecisionResponse
    outcome: OrchestrationOutcome
    invoked_capability: OrchestratedCapability | None
    missing_context: list[OrchestrationContextField]
    message: str
    maintenance_result: MaintenanceEvaluationResponse | None
    support_result: SupportQueryResponse | None
    escalation_result: HumanHandoffResponse | None
    experimental_comparison_result: (
        PredictiveMaintenanceComparisonResponse | None
    )


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


def predictive_maintenance_comparison_response(
    result: MaintenancePredictionComparison,
) -> PredictiveMaintenanceComparisonResponse:
    """Map the distinct service results without creating a final decision."""
    experimental_result = result.experimental_result
    return PredictiveMaintenanceComparisonResponse(
        deterministic=maintenance_response(result.deterministic_result),
        experimental_ml=ExperimentalMaintenanceResponse(
            maintenance_needed_within_90_days_prediction=(
                experimental_result.maintenance_needed_within_90_days_prediction
            ),
            positive_class_probability=(
                experimental_result.positive_class_probability
            ),
            threshold=experimental_result.threshold,
            experimental=experimental_result.experimental,
            artifact_schema_version=experimental_result.artifact_schema_version,
        ),
        comparison=MaintenanceComparisonSignalsResponse(
            deterministic_binary_signal=result.deterministic_binary_signal,
            experimental_ml_binary_signal=result.experimental_ml_binary_signal,
            relationship=result.relationship,
        ),
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


def assistant_response(result: OrchestrationResult) -> AssistantQueryResponse:
    """Map the typed orchestrator result without flattening tool outputs."""
    return AssistantQueryResponse(
        routing_decision=routing_decision_response(result.routing_decision),
        outcome=result.outcome,
        invoked_capability=result.invoked_capability,
        missing_context=list(result.missing_context),
        message=result.message,
        maintenance_result=(
            maintenance_response(result.maintenance_result)
            if result.maintenance_result is not None
            else None
        ),
        support_result=(
            support_response(result.support_result)
            if result.support_result is not None
            else None
        ),
        escalation_result=(
            handoff_response(result.escalation_result)
            if result.escalation_result is not None
            else None
        ),
        experimental_comparison_result=(
            predictive_maintenance_comparison_response(
                result.experimental_comparison_result
            )
            if result.experimental_comparison_result is not None
            else None
        ),
    )


def routing_decision_response(
    decision: RoutingDecision,
) -> RoutingDecisionResponse:
    return RoutingDecisionResponse(
        intent=decision.intent,
        normalized_request=decision.normalized_request,
        matched_intents=list(decision.matched_intents),
        reason=decision.reason,
    )


def handoff_response(result: HumanHandoffResult) -> HumanHandoffResponse:
    return HumanHandoffResponse(
        ticket_id=result.ticket_id,
        reason=result.reason,
        request_summary=result.request_summary,
        status=result.status,
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


@lru_cache(maxsize=1)
def build_predictive_maintenance_comparison_service(
) -> MaintenancePredictionComparisonService:
    """Load and cache the existing experimental comparison capability."""
    return load_default_maintenance_prediction_comparison_service(
        get_predictive_artifact_directory()
    )


def get_predictive_maintenance_comparison_service(
) -> MaintenancePredictionComparisonService:
    """Provide the cached comparison service or a non-sensitive 503 error."""
    try:
        return build_predictive_maintenance_comparison_service()
    except (
        FileNotFoundError,
        ExperimentalArtifactCompatibilityError,
        ExperimentalMaintenancePredictionError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Experimental maintenance comparison is unavailable",
        ) from exc


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


class RuntimeStoredMaintenanceService:
    """Request-time adapter for the existing stored-maintenance service."""

    def __call__(
        self,
        session: Session,
        vehicle_id: int,
        evaluation_date: date,
    ) -> MaintenanceDueResult:
        return evaluate_vehicle_maintenance(
            session=session,
            vehicle_id=vehicle_id,
            evaluation_date=evaluation_date,
        )


class RuntimeRagService:
    """Lazy adapter that prepares the cached RAG service only when selected."""

    def answer_question(self, question: str) -> GroundedAnswer:
        return get_rag_service().answer_question(question)


class RuntimeEscalationService:
    """Adapter for deterministic in-memory handoff creation."""

    def __call__(
        self,
        user_request: str,
        reason: EscalationReason,
    ) -> HumanHandoffResult:
        return create_human_handoff(user_request, reason)


class RuntimePredictiveComparisonService:
    """Lazy adapter that loads the cached experiment only when selected."""

    def compare(
        self,
        feature_input: PredictiveMaintenanceFeatureInput,
    ) -> MaintenancePredictionComparison:
        return get_predictive_maintenance_comparison_service().compare(
            feature_input
        )


def get_orchestration_maintenance_service(
) -> RuntimeStoredMaintenanceService:
    return RuntimeStoredMaintenanceService()


def get_orchestration_rag_service() -> RuntimeRagService:
    return RuntimeRagService()


def get_orchestration_escalation_service() -> RuntimeEscalationService:
    return RuntimeEscalationService()


def get_orchestration_predictive_service(
) -> RuntimePredictiveComparisonService:
    return RuntimePredictiveComparisonService()


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


@asynccontextmanager
async def application_lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare fresh runtime state before accepting requests."""
    initialize_runtime()
    yield


app = FastAPI(
    title="Customer Ownership Copilot API",
    version="0.1.0",
    lifespan=application_lifespan,
)
configure_cors(app)


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
    "/assistant/query",
    response_model=AssistantQueryResponse,
    tags=["assistant"],
)
def query_assistant(
    request: AssistantQueryRequest,
    session: Session = Depends(get_db),
    default_evaluation_date: date = Depends(get_evaluation_date),
    maintenance_service: RuntimeStoredMaintenanceService = Depends(
        get_orchestration_maintenance_service
    ),
    rag_service: RuntimeRagService = Depends(get_orchestration_rag_service),
    escalation_service: RuntimeEscalationService = Depends(
        get_orchestration_escalation_service
    ),
    predictive_service: RuntimePredictiveComparisonService = Depends(
        get_orchestration_predictive_service
    ),
) -> AssistantQueryResponse:
    """Expose deterministic routing and existing capabilities through one API."""
    predictive_input = None
    if request.predictive_maintenance_input is not None:
        try:
            predictive_input = PredictiveMaintenanceFeatureInput(
                **request.predictive_maintenance_input.model_dump()
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Predictive maintenance comparison input is invalid",
            ) from exc

    context = OrchestrationContext(
        vehicle_id=request.vehicle_id,
        evaluation_date=request.evaluation_date or default_evaluation_date,
        session=session,
        predictive_maintenance_input=predictive_input,
    )
    try:
        result = orchestrate_user_request(
            request.message,
            context,
            maintenance_service=maintenance_service,
            rag_service=rag_service,
            escalation_service=escalation_service,
            predictive_comparison_service=predictive_service,
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
    except (
        FileNotFoundError,
        ExperimentalArtifactCompatibilityError,
        ExperimentalMaintenancePredictionError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Experimental maintenance comparison is unavailable",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assistant query could not be completed",
        ) from exc

    return assistant_response(result)


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


@app.post(
    "/maintenance/predictive/compare",
    response_model=PredictiveMaintenanceComparisonResponse,
    tags=["maintenance"],
)
def compare_predictive_maintenance(
    request: PredictiveMaintenanceComparisonRequest,
    comparison_service: MaintenancePredictionComparisonService = Depends(
        get_predictive_maintenance_comparison_service
    ),
) -> PredictiveMaintenanceComparisonResponse:
    """Expose authoritative and experimental signals without merging them."""
    try:
        feature_input = PredictiveMaintenanceFeatureInput(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Predictive maintenance comparison input is invalid",
        ) from exc

    try:
        result = comparison_service.compare(feature_input)
    except (
        FileNotFoundError,
        ExperimentalArtifactCompatibilityError,
        ExperimentalMaintenancePredictionError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Experimental maintenance comparison is unavailable",
        ) from exc

    return predictive_maintenance_comparison_response(result)


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
