# Architecture Decisions

## Decision 1: Use modular router architecture

Date:
2026-08-05

Decision:

Use a custom router connecting specialized modules.

Modules:
- RAG
- Predictive maintenance
- Recommendations
- Escalation

Reason:

This provides:
- Better testing
- Easier debugging
- More explainable behaviour

Rejected:

Full multi-agent architecture initially.

Reason:

Too complex for the timeline and unnecessary for MVP.

---

## Decision 2: Build deterministic logic first

Date:
2026-08-05

Decision:

Implement normal Python functions before adding LLM capabilities.

Reason:

Business logic should remain reliable even when an LLM is unavailable.

---

## Decision 3: Synthetic data only

Date:
2026-08-05

Decision:

Use synthetic or publicly usable datasets.

Reason:

Avoid confidential information and make the project reproducible.

---

## Decision 4: Prioritize MVP completion

Date:
2026-08-05

Decision:

Prefer a smaller working system over many incomplete features.

Reason:

A complete explainable project has more value than unnecessary complexity.

## Decision 5: Tool-Orchestrated Architecture

Date:
2026-08-05

Decision:

Use an orchestrator with specialized tools/services instead of independent AI agents.

Reason:

Provides better testing, reliability, and explainability while still demonstrating agentic behaviour.

Future possibility:

A graph-based agent framework may be evaluated if the workflow complexity requires it.

---

## Decision 6: Keep predictive ML experimental and deterministic rules authoritative

Date:
2026-08-17

Decision:

Keep the deterministic maintenance evaluator as the authoritative MVP mechanism.
Retain Logistic Regression only as an experimental complementary probability
signal, exposed beside the deterministic result without a hybrid/final decision.

Reason:

The model improved held-out recall and exceeded the predefined ROC-AUC boundary,
but it failed the frozen overall useful-value gate because its F1 improvement was
below the required absolute 0.05. The result comes from controlled synthetic data
and does not establish real-world predictive-maintenance accuracy.

Rejected:

Replacing or overriding deterministic maintenance status with the experimental
model.

---

## Decision 7: Use explicit deterministic routing and structured orchestration

Date:
2026-08-18

Decision:

Implement Phase 4 as a small deterministic intent classifier followed by an
explicit orchestrator that invokes existing tools and services. Dependencies and
context remain route-specific, and orchestration returns typed structured
results rather than flattening every capability into free text.

The orchestrator preserves grounded RAG answers and source metadata, creates
human handoffs through a deterministic local mock service, and invokes the
predictive-maintenance comparison only for explicit experimental/ML intent. The
experimental result remains non-authoritative and separate from deterministic
maintenance.

Expose this flow through `POST /assistant/query` while retaining the existing
direct endpoints.

Reason:

The current routing vocabulary is small enough for explainable deterministic
rules. Explicit context requirements prevent unrelated routes from inheriting
dependencies, structured results preserve each capability's semantics, and
ambiguous or unsupported requests can stop safely without arbitrary tool
execution.

Rejected:

- Autonomous agents or a multi-agent architecture
- LLM intent classification or LLM tool calling for MVP routing
- LangChain or LangGraph agent frameworks without demonstrated workflow need
- Reconstructing grounded RAG output or discarding its sources
- A real CRM integration for the bounded mock handoff capability
- Automatically invoking experimental ML for ordinary maintenance requests
- Replacing direct APIs with only the unified assistant endpoint

---

## Decision 8: Build one typed ownership dashboard around the unified assistant

Date:
2026-08-18

Decision:

Implement Phase 5 as one responsive React, Vite, and TypeScript ownership
dashboard with an embedded assistant. Use a small native-fetch client with
runtime response validation and a Vite development proxy to the existing
FastAPI `POST /assistant/query` endpoint.

Render each structured orchestration result with a dedicated presentation:
authoritative deterministic maintenance, grounded support with sources, local
mock handoff, and explicitly experimental predictive comparison. Preserve
context-required, unsupported, clarification, loading, and error outcomes
without adding frontend intent classification.

Reason:

A single polished ownership workspace makes the proof of concept easy to
understand and demonstrate while keeping the backend as the source of routing
and business truth. Typed boundaries prevent capability results from being
silently flattened or confused, and the Vite proxy supports local development
without changing backend CORS solely for the frontend.

Rejected:

- A generic chatbot or raw API-response interface
- Frontend routing or intent classification that competes with the backend
- Combining deterministic and experimental maintenance into a final status
- Hiding the synthetic-data, failed-gate, or local mock-handoff limitations
- Adding React Router, Redux, a large UI framework, or a data-fetching framework
  without demonstrated need

---

## Decision 9: Bootstrap deterministic local runtime state explicitly

Date:
2026-08-18

Decision:

Use a small environment-driven configuration boundary and FastAPI lifespan
bootstrap for fresh runtimes. Anchor default SQLite and generated-artifact paths
to the backend directory, create missing tables, apply the existing idempotent
demo seed, and reuse or reconstruct the frozen experimental predictive artifact
before accepting requests. Configure CORS from exact allowed origins with safe
local defaults, no wildcard production default, and no credentials.

Reason:

A fresh container or cloud filesystem must not depend on files generated on a
developer machine or on its process working directory. Explicit startup
preparation makes failures visible, preserves deterministic seed and experiment
semantics, and keeps deployment configuration understandable without adding a
settings framework, database migration platform, or model registry.

Rejected:

- Committing runtime SQLite databases or generated model binaries
- Silently changing prediction behavior when an artifact is missing
- Replacing SQLite or adding a large configuration framework for this phase
- Permissive wildcard CORS or browser credential support that the product does
  not require

---

## Decision 10: Keep service recommendations deterministic and non-diagnostic

Date:
2026-08-18

Decision:

Implement service-type recommendations as a small rule-based application
service over stored vehicle context and the existing authoritative maintenance
result. Keep scheduled status, recommended next service, and experimental ML as
three separate meanings. Route explicit recommendation and long-trip requests
deterministically and return typed ordered recommendations with explanations.

Reason:

The proof of concept has enough trustworthy context to recommend bounded
service or preventive-inspection categories, but not to diagnose component
failures or claim manufacturer-specific schedules. Named demo/MVP thresholds
remain easy to test, explain, and revise without introducing an LLM decision
boundary.

Rejected:

- Using Gemini or experimental ML to select service recommendations
- Inventing faults, sensor readings, prices, dealer packages, or replacement
  advice
- Combining maintenance status and recommendations into a hybrid/final status

---

## Decision 11: Use bounded structured application logging

Date:
2026-08-18

Decision:

Use one standard-library JSON application logger plus FastAPI request
middleware. Assign or safely reuse an `X-Request-ID`, expose it in responses,
and record request lifecycle, assistant routing outcomes, runtime bootstrap,
readiness, shutdown, and unexpected failure events. Configure severity with
`LOG_LEVEL` and fall back clearly to `INFO` for invalid values.

Operational logs contain only an approved metadata field set. They exclude
request bodies, assistant messages, predictive features, retrieved text,
generated answers, handoff summaries, database records, and secrets.

Reason:

The deployed proof of concept needs enough production diagnostics to correlate
requests and understand routing, outcomes, latency, and startup health without
adding infrastructure or collecting customer content.

Rejected:

- Heavy metrics, tracing, collector, or external logging infrastructure
- Database-backed audit logging
- Logging request/response bodies or capability content
- Swallowing unexpected exceptions to manufacture successful responses
