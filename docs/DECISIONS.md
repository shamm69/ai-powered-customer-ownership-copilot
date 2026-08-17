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
