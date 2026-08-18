# Agentic Customer Ownership Copilot

A deployed proof of concept for bringing vehicle maintenance, service guidance,
grounded ownership support, and escalation into one customer-facing workspace.

- **Frontend:** https://ai-powered-customer-ownership-copil.vercel.app/
- **Backend:** https://ai-powered-customer-ownership-copilot.onrender.com/
- **Health:** https://ai-powered-customer-ownership-copilot.onrender.com/health

The project demonstrates explicit AI-assisted tool orchestration without making
the business-critical maintenance decision depend on an LLM or experimental
model.

## Project overview

Vehicle owners often have to combine service records, maintenance schedules,
manuals, FAQs, and support channels to answer a simple question: **what does my
vehicle need, and what should I do next?**

The Customer Ownership Copilot provides one responsive ownership portal for a
seeded demo vehicle. A typed assistant request is classified by a deterministic
router, executed by an explicit orchestrator, and returned as a structured
capability result. Ambiguous, unsupported, and missing-context requests remain
explicit outcomes instead of triggering an arbitrary tool.

## Architecture

```text
User
  -> React/Vite customer ownership portal
  -> FastAPI POST /assistant/query
  -> deterministic intent router
  -> explicit orchestrator
  -> selected service/capability
  -> structured API response
  -> capability-specific frontend result card
```

The orchestrated capabilities are:

1. Authoritative deterministic stored-vehicle maintenance
2. Deterministic service recommendations
3. Confidence-gated grounded support/RAG
4. Local mock human handoff
5. Explicitly experimental predictive-maintenance comparison

This is **not an autonomous multi-agent system**. It uses no LLM intent routing,
LLM tool calling, LangChain agent, or LangGraph workflow. Gemini is used only
inside the grounded answer-generation boundary after deterministic retrieval
and confidence checks. Deterministic maintenance remains authoritative; the ML
experiment cannot override it and produces no combined final decision.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for diagrams and component
boundaries.

## Technology stack

| Area | Technology |
| --- | --- |
| Backend | Python 3.13, FastAPI, Pydantic, Uvicorn |
| Persistence | SQLAlchemy, SQLite |
| Frontend | React, Vite, TypeScript, native `fetch` |
| RAG | Markdown corpus, `sentence-transformers/all-MiniLM-L6-v2`, cosine similarity, Gemini |
| ML experiment | scikit-learn, `StandardScaler`, `LogisticRegression`, joblib |
| Deployment | Docker, Render, Vercel |
| Verification | pytest, Vitest, Testing Library, TypeScript, Oxlint |

## Capabilities

### Authoritative maintenance

Stored synthetic customer, vehicle, and scheduled-service records are evaluated
with pure distance- and time-based rules. Results preserve the status (`Not
Due`, `Due Soon`, or `Overdue`), kilometres travelled and remaining, months
remaining, and explanatory reasons. This deterministic result is the
authoritative MVP maintenance decision.

### Service recommendation

A separate deterministic layer answers **what service or inspection should be
considered**. It can return Periodic Maintenance Service, Pre-Trip Inspection,
Tyre Inspection/Rotation, Battery Health Check, or No Service Required with an
ordered priority and supporting factors.

These are bounded demo/MVP rules based only on stored context, authoritative
maintenance status, vehicle age, distance since service, and explicit long-trip
intent. They are not manufacturer schedules, prices, fault diagnoses, or
replacement advice.

### Grounded support/RAG

The support path loads a small controlled Markdown corpus, creates stable
section-aware chunks, embeds them locally with MiniLM, and ranks them using
cosine similarity. Confidence gating decides whether the evidence supports an
answer. Supported context is passed to Gemini for grounded generation and the
response preserves document, section, source, and chunk metadata.

If retrieval confidence is insufficient, the service returns a deterministic
unsupported fallback with no fabricated sources and does not call Gemini.

### Human handoff

Explicit handoff intent creates a typed local mock result containing a ticket
reference, reason, request summary, and status. No CRM, dealer, email, SMS,
appointment, or call-centre system is contacted.

### Experimental predictive maintenance

The Technical Preview compares authoritative deterministic maintenance with a
90-day experimental probability from a persisted `StandardScaler` +
`LogisticRegression` pipeline. The experiment used 1,500 deterministic
synthetic snapshots, a frozen train/validation/test process, and a threshold of
`0.19` selected on validation data only.

The model **failed the predefined useful-value/replacement gate**. It is retained
only as a complementary probability/risk-ranking demonstration. Synthetic-data
results do not establish real-world predictive accuracy, deterministic rules
remain authoritative, and no hybrid or final maintenance status exists. The
ignored artifact can be reconstructed reproducibly from the frozen experiment
definition when absent.

## Repository structure

```text
.
|-- backend/
|   |-- app/                     # FastAPI, domain services, routing, RAG, ML
|   |-- knowledge/               # Controlled Markdown support corpus
|   |-- tests/                   # Backend unit, API, integration, runtime tests
|   |-- Dockerfile               # Production backend image
|   |-- requirements-runtime.txt # Runtime-only dependencies
|   `-- requirements.txt         # Runtime + test dependencies
|-- frontend/
|   |-- src/api/                 # Typed native-fetch client
|   |-- src/components/          # Portal, assistant, and result-card UI
|   |-- src/types/               # Assistant API contracts
|   `-- package.json             # Vite scripts and frontend dependencies
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- DECISIONS.md
|   |-- PROGRESS.md
|   `-- PROJECT_CONTEXT.md
|-- AGENTS.md
`-- README.md
```

Generated SQLite files, Python environments, frontend build output, secrets,
and predictive artifacts are intentionally ignored by Git.

## Local setup

### Backend

Python 3.13 is the tested local and container runtime.

```bash
git clone https://github.com/shamm69/ai-powered-customer-ownership-copilot.git
cd ai-powered-customer-ownership-copilot
python -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Install and run:

```bash
python -m pip install -r backend/requirements.txt
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Startup creates missing SQLite tables, applies the idempotent demo seed, and
reuses or reconstructs the frozen predictive artifact. Set `GEMINI_API_KEY`
before using the support/RAG capability; non-support capabilities do not require
that key. Once RAG is prepared, a low-confidence query returns its deterministic
fallback without making a Gemini generation call.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the frontend on port `5173` by default. In development, frontend
requests to `/api/...` are proxied to `http://127.0.0.1:8000`; use
`BACKEND_PROXY_TARGET` to override that development target. No backend CORS
change is required for this proxy workflow.

## Environment variables

| Variable | Purpose | Default/requirement |
| --- | --- | --- |
| `GEMINI_API_KEY` | Gemini credential used to prepare grounded support | Required for the RAG service; never expose to the frontend |
| `GEMINI_MODEL` | Gemini model name | `gemini-3.5-flash-lite` |
| `ALLOWED_FRONTEND_ORIGINS` | Comma-separated exact browser origins | Local Vite origins; no wildcard |
| `CUSTOMER_OWNERSHIP_DATABASE_PATH` | SQLite runtime path | `backend/customer_ownership.db` |
| `PREDICTIVE_MAINTENANCE_ARTIFACT_DIRECTORY` | Generated experimental artifact directory | `backend/artifacts/predictive_maintenance` |
| `LOG_LEVEL` | Application JSON log level | `INFO` |
| `RAG_TOP_K` | Number of retrieved chunks considered | `3` |
| `RAG_MINIMUM_SIMILARITY` | Retrieval confidence threshold | `0.5` |
| `PORT` | Uvicorn port in the container/cloud runtime | `8000` |
| `VITE_API_BASE_URL` | Browser-facing production API base URL | `/api` when unset |
| `BACKEND_PROXY_TARGET` | Vite development proxy target | `http://127.0.0.1:8000` |

Use runtime/platform secret configuration for `GEMINI_API_KEY`; do not commit an
`.env` file or put server secrets in `VITE_*` variables.

## Docker

Build the backend using `backend/` as the context:

```bash
docker build -t customer-ownership-copilot-backend backend
docker run --rm -p 8000:8000 \
  -e GEMINI_API_KEY="<runtime-secret>" \
  -e ALLOWED_FRONTEND_ORIGINS="http://localhost:5173" \
  customer-ownership-copilot-backend
```

The image uses Python 3.13 slim, installs runtime-only dependencies, prefetches
the exact MiniLM model at build time, and runs Uvicorn as a non-root user. The
controlled knowledge corpus is included, while host databases, environments,
tests, and generated model artifacts are excluded. A writable `/app/runtime`
holds the generated SQLite database and reconstructed predictive artifact.
Uvicorn binds to `0.0.0.0`, respects dynamic `PORT`, and the image health check
calls `/health`.

The development machine did not have a Docker-compatible local engine, so the
image was not claimed as locally container-verified. Its real build and runtime
contract were validated by the successful remote Render Docker build and public
deployment.

## Deployment

```text
Browser -> Vercel React/Vite frontend -> Render Docker/FastAPI backend
```

- Vercel hosts the static frontend and supplies the public backend base URL.
- Render builds `backend/Dockerfile`, supplies runtime environment variables,
  starts the backend, and exposes `/health`.
- Exact-origin CORS permits configured frontend origins only; credentials are
  disabled because the proof of concept has no authentication.
- Render's free tier may sleep after inactivity, so the first request can take
  longer while the service cold-starts.

## Testing

Final recorded verification:

- Backend pytest suite: **460 passed**
- Frontend Vitest suite: **47 passed**
- Frontend TypeScript typecheck: **passed**
- Frontend Oxlint: **passed**
- Frontend production build: **passed**
- Python `pip check`: **clean**

Run the checks locally:

```bash
cd backend
python -m pytest -q
python -m pip check

cd ../frontend
npm test
npm run typecheck
npm run lint
npm run build
```

## Observability

The FastAPI application emits small JSON logs using Python's standard logging
library. Request middleware assigns or safely reuses an `X-Request-ID`, returns
it in the response, and logs method, path, status, and monotonic duration.
Assistant completion events record only routed intent, invoked capability,
outcome, and whether context was missing. Startup, database bootstrap,
predictive-artifact preparation, readiness, shutdown, and unexpected failures
are also logged.

Raw user messages, request bodies, predictive features, RAG chunks and answers,
handoff summaries, database records, environment secrets, and API keys are not
logged. External log aggregation and distributed tracing are intentionally out
of scope.

## Limitations

- Seeded synthetic customer, vehicle, and service history; no real customer data
- No authentication, accounts, authorization, or production customer isolation
- SQLite demo persistence, not a production multi-tenant data platform; hosted
  runtime state may reset with the instance lifecycle or redeployment
- No live telematics, sensor data, diagnostics, warranty, pricing, or booking
- No real dealer, CRM, email, SMS, or call-centre integration
- Recommendation thresholds are explainable demo/MVP rules, not manufacturer schedules
- Small controlled RAG corpus rather than unrestricted automotive knowledge
- Gemini availability and correctness remain external provider dependencies
- Predictive ML uses synthetic data and failed its replacement gate
- No manufacturer-authoritative diagnosis or replacement advice
- Render free-tier cold starts after inactivity
- No autonomous agents, LLM routing, or LLM tool calling

## Suggested demo flow

1. Introduce the seeded vehicle and ownership dashboard.
2. Use **Check maintenance** to show the authoritative scheduled-service result.
3. Ask **What service should I get?** or use the long-trip action to show a
   deterministic recommendation and its supporting factors.
4. Ask a corpus-supported warning-light or maintenance question and inspect the
   grounded source titles and sections.
5. Ask an unrelated question to demonstrate the honest unsupported fallback.
6. Request human support and explain the structured local mock handoff.
7. Open **Technical Preview**, supply the eight explicit demo inputs, and show
   deterministic status beside the secondary experimental probability without a
   combined decision.
8. Close with the deterministic router/orchestrator architecture, deployment,
   test coverage, and truthful limitations.
