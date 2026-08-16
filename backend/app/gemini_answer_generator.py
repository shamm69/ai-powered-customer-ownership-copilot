"""Google Gemini implementation of the grounded-answer generator boundary."""

import os
from typing import Any, Protocol

GEMINI_API_KEY_ENVIRONMENT_VARIABLE = "GEMINI_API_KEY"
GEMINI_MODEL_ENVIRONMENT_VARIABLE = "GEMINI_MODEL"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


class GeminiConfigurationError(ValueError):
    """Raised when required Gemini adapter configuration is invalid."""


class GeminiGenerationError(RuntimeError):
    """Raised when Gemini cannot provide usable answer text."""


class _GeminiModels(Protocol):
    def generate_content(self, *, model: str, contents: str) -> Any:
        """Generate model content."""


class _GeminiClient(Protocol):
    models: _GeminiModels


class GeminiAnswerGenerator:
    """Synchronous Gemini adapter satisfying the AnswerGenerator protocol."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_name: str | None = None,
        client: _GeminiClient | None = None,
    ) -> None:
        configured_api_key = (
            os.getenv(GEMINI_API_KEY_ENVIRONMENT_VARIABLE)
            if api_key is None
            else api_key
        )
        if not configured_api_key or not configured_api_key.strip():
            raise GeminiConfigurationError(
                f"{GEMINI_API_KEY_ENVIRONMENT_VARIABLE} must be configured"
            )

        configured_model = (
            os.getenv(
                GEMINI_MODEL_ENVIRONMENT_VARIABLE,
                DEFAULT_GEMINI_MODEL,
            )
            if model_name is None
            else model_name
        )
        if not configured_model.strip():
            raise GeminiConfigurationError("Gemini model name must not be blank")

        self.model_name = configured_model.strip()
        self._client = client or self._create_client(configured_api_key.strip())

    @staticmethod
    def _create_client(api_key: str) -> _GeminiClient:
        from google import genai

        try:
            return genai.Client(api_key=api_key)
        except Exception as error:
            raise GeminiConfigurationError(
                "Unable to initialize the Gemini client"
            ) from error

    def generate(self, prompt: str) -> str:
        """Generate plain answer text using the configured Gemini model."""
        if not prompt.strip():
            raise ValueError("Gemini prompt must not be empty or blank")

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
        except Exception as error:
            raise GeminiGenerationError("Gemini answer generation failed") from error

        generated_text = getattr(response, "text", None)
        if not isinstance(generated_text, str) or not generated_text.strip():
            raise GeminiGenerationError("Gemini returned no usable answer text")
        return generated_text.strip()
