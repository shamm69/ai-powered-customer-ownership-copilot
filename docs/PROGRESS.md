# Project Progress

## Current Phase

Phase 6 in progress — deterministic service recommendations complete

## Current Task

Phase 6.4.1 — Deterministic service recommendations and quick-action routing
hardening are complete. Phase 6 remains in progress.

## Authoritative Roadmap

- Phase 0 — Environment and workflow setup
- Phase 1 — Python, FastAPI, and deterministic domain logic
- Phase 2 — Predictive-maintenance experiment
- Phase 3 — RAG pipeline
- Phase 4 — Router and tool integration
- Phase 5 — Frontend
- Phase 6 — Observability, Docker, documentation, and demo

Historical implementation labels are retained below for accuracy. SQLite,
persistence, and data-layer work was previously labeled Phase 2. RAG was then
completed before the missing original predictive-maintenance scope, which was
later completed under the temporary Phase 2.5 label. Completed work and Git
history were not renamed or redone; Phase 2.5 is not an additional permanent
roadmap phase.

## Completed

### 2026-08-18 — Phase 6.4.1

- Added an explainable stored-vehicle service recommendation capability that
  reuses authoritative deterministic maintenance and returns ordered service or
  preventive-inspection categories with priority, reasons, and supporting
  factors.
- Added bounded demo/MVP rules for periodic maintenance, explicit long-trip
  inspection, distance-based tyre inspection/rotation, age-based battery health
  checks, and a truthful no-service-required result. These are not manufacturer
  schedules or mechanical diagnoses.
- Integrated recommendation through deterministic routing, explicit
  orchestration, the typed `POST /assistant/query` response, and a dedicated
  frontend result card without changing maintenance or experimental-ML
  semantics.
- Aligned every visible quick action with a canonical phrase recognized by the
  deterministic router, including long-trip recommendation and human handoff.
- Completed the bounded capability with 452 backend and 46 frontend tests
  passing, plus clean backend dependency, frontend typecheck, lint, and
  production build results.

### 2026-08-18 — Phase 6.1

- Added small environment-driven runtime configuration for the SQLite database
  path, generated predictive-artifact directory, and exact allowed frontend
  origins while preserving convenient local defaults.
- Added FastAPI lifespan preparation that creates missing database tables,
  applies the existing deterministic idempotent demo seed, and fails startup
  clearly if essential initialization cannot complete.
- Added explicit predictive-artifact preparation that reuses an existing valid
  artifact pair or reconstructs the frozen experimental pipeline and metadata
  when both files are absent. The `0.19` threshold, feature order, failed
  useful-value gate, and deterministic MVP authority remain unchanged.
- Added restricted FastAPI CORS middleware with exact configured origins, no
  wildcard production default, and no credential support.
- Kept runtime SQLite databases and generated model artifacts out of source
  control.
- Completed the bounded foundation with 428 backend tests passing in the
  project-local Python 3.13.5 `.venv`; `pip check` reports no broken
  requirements. Phase 6 remains in progress.

### 2026-08-18 — Phase 5

- Added a responsive React, Vite, and TypeScript frontend under `frontend/`
  with strict typed contracts, a native-fetch API client, and a Vite development
  proxy for the FastAPI backend.
- Built a polished automotive ownership dashboard around the seeded Aster
  Motors Comet demo vehicle, with clear vehicle context, quick actions, and the
  unified ownership assistant as the primary interaction.
- Integrated the typed `POST /assistant/query` flow without adding frontend
  intent classification or duplicating backend routing and orchestration.
- Added dedicated presentations for authoritative deterministic maintenance,
  grounded support answers and source metadata, local mock human handoffs, and
  the explicitly experimental predictive-maintenance comparison.
- Added a truthful eight-field predictive experiment input flow with no hidden
  defaults. The UI keeps deterministic and experimental results separate,
  states that the model uses synthetic data and failed its replacement gate,
  and never produces a hybrid or final maintenance status.
- Preserved confidence-gated RAG fallback behavior, visible mock-handoff
  disclaimers, friendly validation/network/provider errors, loading states,
  and context-required, unsupported, and clarification-required outcomes.
- Completed responsive and interaction polish for desktop, narrower laptop,
  tablet, and mobile-width layouts without adding a router, global state
  library, large UI framework, or fabricated product capabilities.
- Restored the ignored project-local `.venv` with installed Python 3.13.5 and
  the unchanged backend requirements; `pip check` reports no broken
  requirements.
- Completed Phase 5 with 412 backend tests and 38 frontend tests passing, plus
  clean frontend typecheck, lint, and production build results.
- Verified FastAPI and Vite together through the Vite proxy: health,
  authoritative stored-vehicle maintenance, a real grounded Gemini answer with
  controlled-corpus sources, deterministic unsupported support fallback with
  no sources, structured mock handoff, and the real persisted experimental
  comparison at its stored `0.19` threshold all succeeded.
- Automated rendered-browser screenshots were unavailable in the execution
  environment. Live server checks, component rendering tests, and source-level
  responsive review were completed instead; this did not require a product-code
  workaround.

### 2026-08-18 — Phase 4

- Added a small deterministic routing classifier for stored-vehicle
  maintenance, support knowledge, explicit experimental predictive comparison,
  human handoff, unsupported requests, and clarification-required requests.
- Added an explicit orchestrator that invokes existing tools and services using
  route-specific dependencies and context rather than autonomous agents, LLM
  intent classification, or LLM tool calling.
- Integrated authoritative stored-vehicle deterministic maintenance, grounded
  support RAG, deterministic mock human handoff, and the explicitly
  experimental predictive-maintenance comparison.
- Preserved confidence-gated RAG fallback behavior and grounded source metadata.
- Preserved deterministic maintenance as the authoritative MVP result. The ML
  signal requires explicit experimental intent, remains separate, and never
  creates or overrides a final or hybrid maintenance status.
- Added typed `POST /assistant/query` orchestration while retaining all existing
  direct maintenance, support, predictive-comparison, and health endpoints.
- Added cross-route integration and edge-case hardening for routing precedence,
  missing context, tool non-invocation, RAG grounding, experimental ML
  boundaries, escalation boundaries, and HTTP outcome semantics.
- Completed Phase 4 with 412 backend tests passing in the project-local Python
  3.12.10 `.venv`; `pip check` reports no broken requirements.

### 2026-08-17 — Phase 2.5

- Completed the missing original predictive-maintenance experiment scope after
  the persistence work had already been labeled Phase 2 and RAG had been
  completed as Phase 3. Existing completed work and commit history were not
  relabeled or redone.
- Generated 1,500 deterministic synthetic vehicle snapshots with an independent
  binary target, `maintenance_needed_within_90_days` (553 positive and 947
  negative rows), and confirmed through lightweight analysis that the dataset
  was learnable but non-trivial with no configured diagnostic warnings.
- Reused the unchanged deterministic maintenance evaluator as the baseline,
  mapping `not_due` to negative and `due_soon`/`overdue` to positive.
- Trained one CPU-friendly `StandardScaler` + `LogisticRegression` pipeline on a
  deterministic stratified 70/15/15 split: 1,050 training, 225 validation, and
  225 held-out test rows.
- Selected the experimental probability threshold of `0.19` using validation
  data only, then evaluated both systems once on the held-out test partition.
- Held-out deterministic results: 47.24% precision, 72.29% recall, 57.14% F1,
  and 62.55% balanced accuracy.
- Held-out experimental ML results: 43.95% precision, 83.13% recall, 57.50% F1,
  60.58% balanced accuracy, 73.84% ROC-AUC, and 69.03% average precision.
- Applied the predefined useful-value gate: F1 improvement of at least 0.05
  failed, recall at least equal to baseline passed, ROC-AUC of at least 0.70
  passed, and the overall gate failed.
- Retained the fitted pipeline and transparent metadata as ignored local
  experimental artifacts; generated artifacts are not committed to Git.
- Added an immutable experimental prediction service, a side-by-side comparison
  service, and typed `POST /maintenance/predictive/compare` handling.
- The comparison preserves the original deterministic result and experimental
  90-day probability signal separately. It creates no hybrid/final maintenance
  decision and returns HTTP 503 when the experimental artifact is unavailable.
- Confirmed the deterministic evaluator remains the authoritative MVP
  maintenance mechanism. ML is retained only as an experimental complementary
  higher-recall/risk-ranking signal.
- The experiment uses controlled synthetic data and does not establish
  real-world predictive-maintenance accuracy.
- Reconciled dependencies in the isolated project-local `.venv` using Python
  3.12.10; `pip check` reported no broken requirements.
- Completed Phase 2.5 with 291 backend tests passing.

### 2026-08-17 — Phase 3

- Added a small controlled automotive support knowledge corpus and typed document loading.
- Added deterministic Markdown-aware chunking with stable source and section metadata.
- Added local `sentence-transformers/all-MiniLM-L6-v2` embeddings and immutable indexed chunks.
- Added exact in-memory semantic retrieval using cosine-similarity ranking.
- Added configurable retrieval confidence gating and a deterministic unsupported-query fallback.
- Added a provider-neutral `AnswerGenerator` interface and a Gemini runtime adapter using `google-genai`.
- Integrated the complete retrieval and grounded-answer pipeline through `RagService`.
- Added typed `POST /support/query` request and response handling with source metadata for grounded answers.
- Added lazy, cached RAG preparation so the corpus is not reloaded and re-embedded for every request.
- Kept the implementation lightweight: no FAISS, Chroma, LangChain, LangGraph, or autonomous agents.
- Verified the real `sentence-transformers/all-MiniLM-L6-v2` model loaded successfully and real Gemini generation succeeded.
- Verified a supported query returned HTTP 200 with a grounded answer and sources.
- Verified an unrelated query returned HTTP 200 with the deterministic fallback and empty sources, without calling Gemini.
- Verified `/health` and the maintenance endpoint continued to work.
- Completed Phase 3 with 153 backend tests passing.

### 2026-08-11 — Phase 2

- Added the SQLite and SQLAlchemy database foundation.
- Added Customer, Vehicle, and ServiceRecord models with tested relationships.
- Added a small deterministic synthetic seed dataset.
- Added vehicle lookup and latest scheduled-service queries.
- Connected stored vehicle and service data to the maintenance evaluator through an application service.
- Added `GET /vehicles/{vehicle_id}/maintenance` for stored-data maintenance evaluation.
- Added isolated database, query, service, and API tests.
- Completed Phase 2 with 51 tests passing.

### 2026-08-06 — Phase 1

- Exposed the deterministic maintenance evaluator through `POST /maintenance/evaluate`.
- Added typed request and response validation without coupling domain logic to FastAPI.
- Added API tests for valid statuses, invalid inputs, and non-finite numeric values.
- Completed Phase 1 backend foundation and deterministic maintenance capability.

### 2026-08-05 — Phase 1

- Created a Python 3.12 virtual environment.
- Added the minimal FastAPI application foundation.
- Added a health-check endpoint.
- Added and verified the initial API test.
- Added a pure maintenance due-status evaluator using supplied distance and time intervals.
- Added focused tests for due states, decision reasons, boundaries, and invalid inputs.

### 2026-08-05 — Phase 0

- Verified development environment:
  - Git
  - Python
  - Node.js
  - VS Code
- Created project repository.
- Initialized Git and connected GitHub.
- Created initial documentation structure.
- Configured Codex workflow.
- Added repository instructions.
- Completed Git workflow setup.
- Refined project architecture documentation.
- Aligned architecture wording around a central router/orchestrator invoking tools and services rather than autonomous specialized agents.

## Current Status

- Phase 0 completed.
- Phase 1 completed.
- Persistence/data-layer work completed under its historical Phase 2 label.
- The original Phase 2 predictive-maintenance experiment completed under the
  temporary Phase 2.5 implementation label.
- Phase 3 completed.
- Phase 4 completed.
- Phase 5 completed.
- Phase 6 is in progress; the Phase 6.1 deployment-readiness foundation is
  complete, while Dockerization and deployment have not started.
- FastAPI backend foundation is working and tested.
- The original deterministic maintenance evaluator remains independent of persistence and unchanged.
- Maintenance evaluation is exposed through a typed FastAPI endpoint.
- Stored vehicle maintenance evaluation is exposed through a typed FastAPI endpoint.
- Grounded support-document answers are exposed through typed `POST /support/query` responses with source metadata.
- Unsupported support queries return a deterministic fallback without invoking Gemini.
- The deterministic maintenance evaluator remains authoritative for MVP status;
  predictive ML remains an experimental complementary signal only.
- `POST /maintenance/predictive/compare` exposes both signals without a hybrid
  decision and uses an ignored local artifact with threshold `0.19`.
- `POST /assistant/query` exposes deterministic routing, explicit orchestration,
  and structured capability-specific results without replacing direct APIs.
- Complete backend test suite has 452 tests passing in the repaired
  project-local Python 3.13.5 `.venv`; `pip check` is clean.
- Complete frontend suite has 46 tests passing, with typecheck, lint, and the
  Vite production build also passing.
- The React frontend uses `POST /assistant/query` through a local Vite proxy and
  preserves structured maintenance, grounded support, mock handoff, and
  experimental comparison results.

## Next Steps

- Continue Phase 6 only through the next separately approved bounded task.

## Blockers

None.
