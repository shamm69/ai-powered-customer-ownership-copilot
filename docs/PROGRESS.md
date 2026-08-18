# Project Progress

## Current state

Application implementation, production deployment, lightweight observability,
and final repository documentation are complete. Phase 6 remains open only for
separately authorized final verification and report/presentation work.

Current verification baseline:

- Backend: 460 pytest tests passing
- Frontend: 47 Vitest tests passing
- Frontend typecheck, lint, and production build passing
- Python `pip check` clean
- Backend deployed on Render from the production Dockerfile
- Frontend deployed on Vercel

## Authoritative roadmap

1. Phase 0 — Environment and workflow
2. Phase 1 — Python, FastAPI, and deterministic domain logic
3. Phase 2 — Predictive-maintenance experiment
4. Phase 3 — RAG pipeline
5. Phase 4 — Router and tool integration
6. Phase 5 — Frontend
7. Phase 6 — Production readiness, deployment, documentation, and demo

### Historical labeling note

The implementation history originally labeled SQLite/persistence work as
“Phase 2.” RAG was then completed before the missing original predictive-
maintenance experiment, which was later implemented under the temporary label
“Phase 2.5.” Completed commits were not relabeled or redone.

The roadmap above is authoritative: persistence is supporting application
infrastructure, and the predictive experiment is the final Phase 2 capability.

## Implementation timeline

### Phase 0 — Environment and workflow

- Established Git/GitHub workflow, Python and Node development environments,
  repository instructions, and initial architecture documentation.
- Chose an explicit modular service architecture over autonomous agents.

### Phase 1 — Backend and deterministic foundation

- Added FastAPI, typed Pydantic requests/responses, and `/health`.
- Implemented the pure distance/time maintenance evaluator with `Not Due`, `Due
  Soon`, and `Overdue` outcomes.
- Added SQLAlchemy/SQLite customer, vehicle, and service-record models as
  supporting infrastructure.
- Added deterministic idempotent demo seed data, stored-vehicle queries, the
  maintenance application service, and direct maintenance APIs.

### Phase 2 — Predictive-maintenance experiment

- Generated 1,500 deterministic synthetic vehicle snapshots with an independent
  90-day target.
- Reused deterministic maintenance as the baseline.
- Trained one `StandardScaler` + `LogisticRegression` pipeline using a frozen
  stratified 70/15/15 train/validation/test split.
- Selected threshold `0.19` using validation data only and evaluated once on the
  held-out test set.
- Deterministic held-out results: 47.24% precision, 72.29% recall, 57.14% F1,
  and 62.55% balanced accuracy.
- Experimental held-out results: 43.95% precision, 83.13% recall, 57.50% F1,
  60.58% balanced accuracy, 73.84% ROC-AUC, and 69.03% average precision.
- The predefined overall useful-value/replacement gate failed because the model
  did not achieve the required absolute F1 improvement of 0.05.
- Retained the model only as an experimental comparison signal. Deterministic
  maintenance remains authoritative; no hybrid/final decision exists.
- Added reproducible ignored artifacts, prediction/comparison services, and
  `POST /maintenance/predictive/compare`.

### Phase 3 — Grounded RAG

- Added a controlled Markdown automotive support corpus and deterministic
  section-aware chunking.
- Added local `all-MiniLM-L6-v2` embeddings and exact in-memory cosine retrieval.
- Added configurable confidence gating and deterministic unsupported fallback.
- Added a provider-neutral answer boundary and Gemini adapter.
- Preserved source document, section, source ID, and chunk metadata in typed
  `POST /support/query` responses.
- Avoided FAISS, Chroma, LangChain, LangGraph, and autonomous agent frameworks.

### Phase 4 — Router and tool integration

- Added a small deterministic classifier for maintenance, support, handoff,
  explicit experimental comparison, unsupported, and clarification-required
  intents. Recommendation intent was added later with that bounded capability.
- Added an explicit orchestrator with route-specific dependencies and context.
- Integrated stored maintenance, grounded RAG, mock handoff, and explicit
  experimental comparison without duplicating their internal logic.
- Added the typed unified `POST /assistant/query` endpoint while retaining direct
  capability endpoints.
- Hardened routing conflicts, missing context, non-invocation guarantees, error
  translation, RAG grounding, and experimental authority boundaries.

### Phase 5 — Customer frontend

- Built a responsive React, Vite, and TypeScript ownership portal with a typed
  native-fetch client and runtime response validation.
- Added vehicle context, canonical quick actions, assistant interaction,
  loading/error/context states, and capability-specific result cards.
- Presented maintenance as authoritative, recommendations as bounded demo rules,
  RAG answers with grounded sources, and handoff as a local mock.
- Moved manual predictive inputs and comparison results into a secondary
  Technical Preview with synthetic-data and failed-gate disclosures.
- Completed customer-facing information architecture, responsive behavior,
  accessibility, visual polish, and truthful product copy.
- Verified real full-stack flows through the Vite development proxy.

### Phase 6 — Production readiness and deployment

- Added environment-driven SQLite/artifact paths and exact-origin CORS.
- Added FastAPI lifespan bootstrap for table creation, idempotent seeding, and
  valid-artifact reuse or deterministic reconstruction.
- Added a Python 3.13 production backend Docker image with runtime-only
  dependencies, non-root execution, writable runtime state, MiniLM build-time
  prefetch/offline runtime, dynamic `PORT`, and `/health` health check.
- Validated the image through the successful remote Render build/deployment
  because no Docker-compatible local engine was available on the development
  machine.
- Deployed the React/Vite frontend to Vercel and the Docker/FastAPI backend to
  Render.
- Added deterministic service recommendations for periodic maintenance,
  pre-trip inspection, tyre inspection/rotation, battery health check, and no
  service required.
- Added safe JSON request, assistant-outcome, startup/shutdown, and error logging
  with request IDs and monotonic duration.
- Finalized README, project context, architecture diagrams, decisions, roadmap,
  local setup, deployment, testing, observability, limitations, and demo flow.

## Final capability status

| Capability | Status | Boundary |
| --- | --- | --- |
| Scheduled maintenance | Complete | Authoritative deterministic MVP status |
| Service recommendation | Complete | Deterministic demo/MVP rules; not diagnosis or manufacturer schedule |
| Grounded support/RAG | Complete | Controlled corpus, confidence gated, sources preserved |
| Human handoff | Complete | Local mock only; no external CRM/dealer integration |
| Predictive comparison | Complete as experiment | Synthetic data, failed replacement gate, non-authoritative |
| Router/orchestrator | Complete | Deterministic and explicit; no LLM routing/tool calling |
| Customer frontend | Complete | Public Vercel deployment |
| Backend runtime | Complete | Public Render Docker deployment |
| Lightweight observability | Complete | JSON application logs; no external aggregation |

## Remaining bounded work

- Final verification/report/presentation work only when separately authorized.
- No product functionality is currently marked as missing.

## Blockers

None recorded.
