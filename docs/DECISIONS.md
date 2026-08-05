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