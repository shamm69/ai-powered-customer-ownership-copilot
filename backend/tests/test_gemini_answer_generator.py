"""Tests for the Google Gemini answer-generator adapter."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.gemini_answer_generator import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_API_KEY_ENVIRONMENT_VARIABLE,
    GEMINI_MODEL_ENVIRONMENT_VARIABLE,
    GeminiAnswerGenerator,
    GeminiConfigurationError,
    GeminiGenerationError,
)


class FakeModels:
    def __init__(
        self,
        response_text: object = "Grounded Gemini answer.",
        error: Exception | None = None,
    ) -> None:
        self.response_text = response_text
        self.error = error
        self.calls: list[dict[str, str]] = []

    def generate_content(self, *, model: str, contents: str) -> Any:
        self.calls.append({"model": model, "contents": contents})
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.response_text)


class FakeClient:
    def __init__(self, models: FakeModels | None = None) -> None:
        self.models = models or FakeModels()


def test_generate_uses_default_model_and_returns_trimmed_plain_text() -> None:
    models = FakeModels("  Grounded Gemini answer.  ")
    generator = GeminiAnswerGenerator(
        api_key="test-api-key",
        client=FakeClient(models),
    )

    answer = generator.generate("Use only approved support context.")

    assert answer == "Grounded Gemini answer."
    assert generator.model_name == DEFAULT_GEMINI_MODEL
    assert models.calls == [
        {
            "model": DEFAULT_GEMINI_MODEL,
            "contents": "Use only approved support context.",
        }
    ]


def test_environment_configures_api_key_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_api_keys: list[str] = []
    fake_client = FakeClient()

    def fake_create_client(api_key: str) -> FakeClient:
        created_api_keys.append(api_key)
        return fake_client

    monkeypatch.setenv(GEMINI_API_KEY_ENVIRONMENT_VARIABLE, "environment-key")
    monkeypatch.setenv(GEMINI_MODEL_ENVIRONMENT_VARIABLE, "gemini-custom-model")
    monkeypatch.setattr(
        GeminiAnswerGenerator,
        "_create_client",
        staticmethod(fake_create_client),
    )

    generator = GeminiAnswerGenerator()

    assert created_api_keys == ["environment-key"]
    assert generator.model_name == "gemini-custom-model"


def test_explicit_configuration_overrides_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(GEMINI_API_KEY_ENVIRONMENT_VARIABLE, "environment-key")
    monkeypatch.setenv(GEMINI_MODEL_ENVIRONMENT_VARIABLE, "environment-model")
    generator = GeminiAnswerGenerator(
        api_key="explicit-key",
        model_name="explicit-model",
        client=FakeClient(),
    )

    assert generator.model_name == "explicit-model"


def test_missing_api_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GEMINI_API_KEY_ENVIRONMENT_VARIABLE, raising=False)

    with pytest.raises(
        GeminiConfigurationError,
        match=GEMINI_API_KEY_ENVIRONMENT_VARIABLE,
    ):
        GeminiAnswerGenerator()


@pytest.mark.parametrize("api_key", ["", "   "])
def test_blank_explicit_api_key_is_rejected(api_key: str) -> None:
    with pytest.raises(GeminiConfigurationError, match="must be configured"):
        GeminiAnswerGenerator(api_key=api_key, client=FakeClient())


@pytest.mark.parametrize("model_name", ["", "   "])
def test_blank_model_name_is_rejected(model_name: str) -> None:
    with pytest.raises(GeminiConfigurationError, match="model name must not be blank"):
        GeminiAnswerGenerator(
            api_key="test-api-key",
            model_name=model_name,
            client=FakeClient(),
        )


@pytest.mark.parametrize("prompt", ["", "   ", "\n\t"])
def test_blank_prompt_is_rejected(prompt: str) -> None:
    generator = GeminiAnswerGenerator(
        api_key="test-api-key",
        client=FakeClient(),
    )

    with pytest.raises(ValueError, match="prompt must not be empty or blank"):
        generator.generate(prompt)


def test_provider_exception_is_wrapped() -> None:
    provider_error = RuntimeError("provider detail")
    generator = GeminiAnswerGenerator(
        api_key="test-api-key",
        client=FakeClient(FakeModels(error=provider_error)),
    )

    with pytest.raises(
        GeminiGenerationError,
        match="Gemini answer generation failed",
    ) as error_info:
        generator.generate("Grounded prompt.")

    assert error_info.value.__cause__ is provider_error


@pytest.mark.parametrize("response_text", [None, "", "   ", 42])
def test_blank_or_malformed_provider_output_is_rejected(
    response_text: object,
) -> None:
    generator = GeminiAnswerGenerator(
        api_key="test-api-key",
        client=FakeClient(FakeModels(response_text=response_text)),
    )

    with pytest.raises(GeminiGenerationError, match="no usable answer text"):
        generator.generate("Grounded prompt.")


def test_client_initialization_error_is_wrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialization_error = RuntimeError("initialization detail")

    def fail_to_create_client(api_key: str) -> FakeClient:
        raise GeminiConfigurationError(
            "Unable to initialize the Gemini client"
        ) from initialization_error

    monkeypatch.setattr(
        GeminiAnswerGenerator,
        "_create_client",
        staticmethod(fail_to_create_client),
    )

    with pytest.raises(
        GeminiConfigurationError,
        match="Unable to initialize the Gemini client",
    ) as error_info:
        GeminiAnswerGenerator(api_key="test-api-key")

    assert error_info.value.__cause__ is initialization_error
