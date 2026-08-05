"""Application entry point for the Customer Ownership Copilot API."""

from fastapi import FastAPI

app = FastAPI(
    title="Customer Ownership Copilot API",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Report whether the API process is ready to accept requests."""
    return {"status": "healthy"}
