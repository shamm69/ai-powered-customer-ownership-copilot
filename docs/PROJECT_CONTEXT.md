# Project Context

## Purpose

Agentic Customer Ownership Copilot is a deployed automotive ownership proof of
concept. It gives a vehicle owner one structured interface for scheduled
maintenance status, bounded service recommendations, grounded documentation
support, and a mock human handoff. A separate Technical Preview demonstrates an
experimental predictive-maintenance comparison without presenting ML as the
customer's maintenance authority.

The product addresses fragmented ownership information: service history,
maintenance intervals, manuals, FAQs, and support channels typically require
separate interactions. The project explores how an explicit orchestrator can
unify those capabilities while preserving their different meanings and failure
boundaries.

## Final system

### Customer portal

- Responsive React, Vite, and TypeScript single-page ownership workspace
- Seeded demo customer and selected vehicle context
- Typed native-fetch client with runtime response validation
- Customer quick actions aligned with deterministic backend routing
- Dedicated cards for maintenance, recommendations, grounded support, and mock
  handoff
- Secondary Technical Preview for manual experimental ML inputs and comparison
- Honest loading, context-required, clarification, unsupported, and provider
  failure states

### Backend

- FastAPI and Pydantic HTTP boundary
- Deterministic intent classifier with explicit ambiguity and unsupported states
- Explicit orchestrator with route-specific context and dependencies
- SQLAlchemy/SQLite seeded demo persistence
- Pure distance- and time-based scheduled-maintenance evaluator
- Deterministic service recommendation rules
- Confidence-gated local retrieval plus Gemini grounded answer generation
- Local mock escalation result
- Side-by-side deterministic and experimental predictive comparison
- Fresh-runtime database/artifact bootstrap, exact-origin CORS, and JSON logging

## Architecture

```text
User
-> React/Vite Customer Ownership Portal
-> POST /assistant/query
-> FastAPI validation and runtime dependencies
-> Deterministic Router
-> Explicit Orchestrator
-> One selected capability
-> Typed structured result
-> Capability-specific frontend presentation
```

The router/orchestrator is intentionally not an autonomous multi-agent design.
There is no LLM intent classifier, LLM tool calling, LangChain agent, or
LangGraph workflow. Gemini is isolated to grounded answer generation after
deterministic retrieval and confidence gating.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full component and deployment
diagrams.

## Capability boundaries

### Authoritative scheduled maintenance

Stored vehicle and latest scheduled-service data feed the unchanged pure
maintenance evaluator. Distance and elapsed time produce `not_due`, `due_soon`,
or `overdue` with metrics and reasons. This result is the authoritative MVP
maintenance status.

### Deterministic service recommendation

Recommendation answers a separate question: what service or preventive
inspection should the owner consider? Bounded rules can produce periodic
maintenance, pre-trip inspection, tyre inspection/rotation, battery health
check, or no service required. They use only available context and do not claim
manufacturer schedules, prices, faults, or diagnosis.

### Grounded support/RAG

Three controlled Markdown documents are chunked with stable metadata and
embedded using `sentence-transformers/all-MiniLM-L6-v2`. Exact in-memory cosine
similarity retrieval and a configured confidence threshold determine whether
context supports an answer. Gemini generates only from the grounded prompt;
source metadata is preserved. Insufficient retrieval returns a deterministic
fallback with no Gemini call and no fabricated sources.

### Mock human handoff

Explicit handoff routing creates a typed local reference and status. It does
not contact a CRM, dealer, email, messaging, appointment, or call-centre system.

### Experimental predictive comparison

The experiment uses a deterministic synthetic dataset and a persisted
`StandardScaler` + `LogisticRegression` pipeline for the target
`maintenance_needed_within_90_days`. Its `0.19` threshold was selected using
validation data only. The model improved held-out recall but failed the frozen
overall useful-value/replacement gate because the required F1 improvement was
not achieved.

The feature is therefore explicit, secondary, and non-authoritative. It
preserves deterministic status, ML probability, threshold, binary signals, and
their relationship side by side. It cannot override maintenance and creates no
hybrid/final decision. Synthetic results do not establish real-world accuracy.

## Runtime and deployment

```text
Browser -> Vercel frontend -> Render Docker backend
```

- Frontend: https://ai-powered-customer-ownership-copil.vercel.app/
- Backend: https://ai-powered-customer-ownership-copilot.onrender.com/
- Health: https://ai-powered-customer-ownership-copilot.onrender.com/health

The production backend image uses Python 3.13 slim, Uvicorn, a non-root user,
runtime-only dependencies, and a writable `/app/runtime`. It prefetches the
exact MiniLM model during build and runs Hugging Face/Transformers offline at
runtime. The controlled corpus is copied into the image. Startup creates tables,
idempotently seeds an empty database, and reuses or reconstructs the frozen
experimental artifact before readiness.

The image was validated by the successful remote Render build and deployment;
the development machine did not have a Docker-compatible local engine. Render's
free tier may cold-start after inactivity.

Exact frontend origins are supplied through environment configuration. Gemini
credentials remain backend runtime secrets and are never included in the image
or frontend.

## API surface

Primary frontend contract:

- `POST /assistant/query`

Direct capability endpoints remain available:

- `GET /health`
- `POST /maintenance/evaluate`
- `GET /vehicles/{vehicle_id}/maintenance`
- `POST /support/query`
- `POST /maintenance/predictive/compare`

The unified endpoint supplements rather than replaces the direct APIs.

## Verification state

- Backend pytest suite: 460 passed
- Frontend Vitest suite: 47 passed
- Frontend typecheck, lint, and production build: passed
- Python dependency check: clean
- Backend deployed through Render Docker build
- Frontend deployed through Vercel

## Operational characteristics

- FastAPI lifespan performs essential database and predictive-artifact setup.
- Runtime initialization is deterministic and idempotent for the demo seed.
- Request middleware emits safe JSON lifecycle logs with `X-Request-ID` and
  duration.
- Assistant logs contain routing/capability/outcome metadata, not customer
  content.
- Unexpected errors remain errors; they are logged and not converted into fake
  successful responses.
- No external logging aggregation or distributed tracing is used.

## Constraints and limitations

- Synthetic/public data only; no proprietary or real customer information
- Seeded demo identity and vehicle data; no authentication or customer accounts
- SQLite is suitable for this bounded demo, not production multi-tenancy;
  hosted runtime state may reset with the instance lifecycle or redeployment
- No telematics, real diagnostics, manufacturer schedule, pricing, or warranty
- No real dealer/CRM/booking/messaging integration
- Small controlled support corpus and external Gemini dependency
- Deterministic recommendation rules are demo/MVP rules, not diagnosis
- Experimental ML uses synthetic data and failed its replacement gate
- No autonomous agents or LLM-based routing/tool selection

## Project objective

The final repository is intended to be understandable in a technical review or
interview. It demonstrates deterministic domain design, persistence, RAG,
experimental ML evaluation, typed orchestration, frontend productization,
container deployment, testing, and bounded observability without overstating
what the proof of concept can do.
