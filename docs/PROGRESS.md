# Project Progress

## Current Phase

Phase 3 complete — next phase not started

## Current Task

Define the scope of the next phase before beginning implementation.

## Completed

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
- Phase 2 completed.
- Phase 3 completed.
- FastAPI backend foundation is working and tested.
- The original deterministic maintenance evaluator remains independent of persistence and unchanged.
- Maintenance evaluation is exposed through a typed FastAPI endpoint.
- Stored vehicle maintenance evaluation is exposed through a typed FastAPI endpoint.
- Grounded support-document answers are exposed through typed `POST /support/query` responses with source metadata.
- Unsupported support queries return a deterministic fallback without invoking Gemini.
- Complete backend test suite has 153 tests passing.
- Local `main` is synchronized with `origin/main`.

## Next Steps

- Define the scope of the next phase before beginning implementation.

## Blockers

None.
