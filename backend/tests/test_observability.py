"""Tests for lightweight structured application observability."""

from io import StringIO
import json
import logging
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app import main as main_module
from app.observability import (
    REQUEST_ID_HEADER,
    RequestObservabilityMiddleware,
    configure_application_logging,
    resolve_log_level,
)
from app.runtime_bootstrap import RuntimeBootstrapResult


class RecordingHandler(logging.Handler):
    """Collect log records without depending on their rendered JSON."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_health_response_contains_generated_request_id() -> None:
    with TestClient(main_module.app) as client:
        response = client.get("/health")

    request_id = response.headers[REQUEST_ID_HEADER]
    assert response.status_code == 200
    assert str(UUID(request_id)) == request_id


def test_safe_inbound_request_id_is_reused() -> None:
    with TestClient(main_module.app) as client:
        response = client.get(
            "/health",
            headers={REQUEST_ID_HEADER: "demo-request_123"},
        )

    assert response.headers[REQUEST_ID_HEADER] == "demo-request_123"


def test_unsafe_inbound_request_id_is_replaced() -> None:
    with TestClient(main_module.app) as client:
        response = client.get(
            "/health",
            headers={REQUEST_ID_HEADER: "unsafe request/id"},
        )

    assert response.headers[REQUEST_ID_HEADER] != "unsafe request/id"
    UUID(response.headers[REQUEST_ID_HEADER])


def test_request_completion_log_contains_operational_metadata() -> None:
    recorder = RecordingHandler()
    main_module.application_logger.addHandler(recorder)
    try:
        with TestClient(main_module.app) as client:
            response = client.get(
                "/health",
                headers={REQUEST_ID_HEADER: "completion-test"},
            )
    finally:
        main_module.application_logger.removeHandler(recorder)

    completion = next(
        record
        for record in recorder.records
        if getattr(record, "event", None) == "request_completed"
    )
    assert response.status_code == 200
    assert completion.request_id == "completion-test"
    assert completion.method == "GET"
    assert completion.path == "/health"
    assert completion.status_code == 200
    assert completion.duration_ms >= 0


def test_assistant_log_contains_only_routing_metadata() -> None:
    raw_message = "Give me a private pasta recipe ZXQ-917"
    recorder = RecordingHandler()
    main_module.application_logger.addHandler(recorder)
    try:
        with TestClient(main_module.app) as client:
            response = client.post(
                "/assistant/query",
                json={"message": raw_message},
                headers={REQUEST_ID_HEADER: "assistant-test"},
            )
    finally:
        main_module.application_logger.removeHandler(recorder)

    assistant_record = next(
        record
        for record in recorder.records
        if getattr(record, "event", None) == "assistant_request_completed"
    )
    assert response.status_code == 200
    assert assistant_record.request_id == "assistant-test"
    assert assistant_record.routed_intent == "unsupported"
    assert assistant_record.invoked_capability is None
    assert assistant_record.outcome == "unsupported"
    assert assistant_record.context_missing is False
    assert all(raw_message not in record.getMessage() for record in recorder.records)


def test_unexpected_exception_is_logged_and_not_swallowed() -> None:
    recorder = RecordingHandler()
    logger = logging.getLogger("observability.exception-test")
    logger.handlers.clear()
    logger.addHandler(recorder)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    application = FastAPI()
    application.add_middleware(RequestObservabilityMiddleware, logger=logger)

    @application.get("/failure")
    def fail() -> None:
        raise RuntimeError("sensitive request detail")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get(
            "/failure",
            headers={REQUEST_ID_HEADER: "failure-test"},
        )

    failure = next(
        record
        for record in recorder.records
        if getattr(record, "event", None) == "request_failed"
    )
    assert response.status_code == 500
    assert failure.request_id == "failure-test"
    assert failure.exception_type == "RuntimeError"
    assert "sensitive request detail" not in failure.getMessage()


def test_log_level_configuration_and_invalid_fallback() -> None:
    assert resolve_log_level({"LOG_LEVEL": "debug"}) == (logging.DEBUG, False)
    assert resolve_log_level({"LOG_LEVEL": "verbose"}) == (logging.INFO, True)

    output = StringIO()
    logger = configure_application_logging(
        {"LOG_LEVEL": "verbose"},
        logger_name="observability.level-test",
        stream=output,
    )

    assert logger.level == logging.INFO
    fallback = json.loads(output.getvalue())
    assert fallback["event"] == "invalid_log_level_fallback"
    assert "verbose" not in output.getvalue()


def test_application_lifespan_logs_bootstrap_and_shutdown(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "initialize_runtime",
        lambda: RuntimeBootstrapResult(
            database_seeded=True,
            predictive_artifact_created=False,
        ),
    )
    recorder = RecordingHandler()
    main_module.application_logger.addHandler(recorder)
    try:
        with TestClient(main_module.app) as client:
            assert client.get("/health").status_code == 200
    finally:
        main_module.application_logger.removeHandler(recorder)

    events = [getattr(record, "event", None) for record in recorder.records]
    assert "application_startup_beginning" in events
    assert "database_bootstrap_complete" in events
    assert "predictive_artifact_prepared" in events
    assert "application_ready" in events
    assert "application_shutdown" in events

    database_record = next(
        record
        for record in recorder.records
        if getattr(record, "event", None) == "database_bootstrap_complete"
    )
    artifact_record = next(
        record
        for record in recorder.records
        if getattr(record, "event", None) == "predictive_artifact_prepared"
    )
    assert database_record.database_seeded is True
    assert artifact_record.predictive_artifact_created is False
