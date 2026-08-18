# Architecture Decisions

## 1. Keep scheduled maintenance deterministic and authoritative

**Decision:** Implement distance- and time-based maintenance as pure Python
domain logic. Stored data supplies inputs but does not own the calculation.

**Why:** Scheduled status must remain explainable, testable, and available
without an LLM or experimental model.

**Rejected:** Letting Gemini or predictive ML determine or override `Not Due`,
`Due Soon`, or `Overdue`.

## 2. Use SQLite and deterministic synthetic seed data for the demo

**Decision:** Use SQLAlchemy with SQLite for bounded customer, vehicle, and
service history. Create tables and apply an idempotent synthetic seed at startup.

**Why:** The proof of concept needs realistic persistence and reproducible demo
state without collecting private data or operating production infrastructure.

**Rejected:** Proprietary/customer data, PostgreSQL migration solely for the
demo, or committing a generated runtime database.

## 3. Ground support answers in a controlled corpus

**Decision:** Chunk controlled Markdown documents, embed them locally with
`sentence-transformers/all-MiniLM-L6-v2`, retrieve by cosine similarity, and
apply confidence gating before Gemini generation. Preserve source metadata.

**Why:** Grounding and a deterministic unsupported fallback are safer and more
explainable than unrestricted general automotive answers.

**Rejected:** Calling Gemini without retrieved evidence, fabricating citations,
or adding a vector database/framework without demonstrated need.

## 4. Retain predictive ML only as a failed-gate experiment

**Decision:** Keep the frozen `StandardScaler` + `LogisticRegression` pipeline,
validation-selected threshold `0.19`, and side-by-side comparison only. Rebuild
the ignored artifact reproducibly from fixed synthetic data and seeds when
absent.

**Why:** The experiment improved recall and exceeded its ROC-AUC boundary but
failed the predefined overall replacement gate because F1 improvement was below
0.05. Synthetic results do not prove real-world accuracy.

**Rejected:** Replacing deterministic maintenance, tuning on held-out test data,
committing generated binaries, or creating a hybrid/final status.

## 5. Use a deterministic router and explicit orchestrator

**Decision:** Classify a small routing vocabulary with explainable rules, then
invoke one bounded service through an explicit orchestrator. Treat ambiguity,
unsupported requests, and missing context as typed outcomes.

**Why:** Current workflow complexity does not justify probabilistic routing or
an agent framework. Explicit orchestration preserves service boundaries and is
easy to test.

**Rejected:** Autonomous/multi-agent architecture, LLM intent classification,
LLM tool calling, LangChain agents, LangGraph, and arbitrary fallback to RAG.

## 6. Keep recommendations deterministic, bounded, and non-diagnostic

**Decision:** Recommend only predefined service/inspection categories using
authoritative maintenance, stored vehicle context, and explicit long-trip
intent. Return ordered priority, reason, and supporting factors.

**Why:** Available demo data supports explainable preventive suggestions, not
fault diagnosis or manufacturer-specific service schedules.

**Rejected:** Gemini/ML recommendation selection, invented faults, prices,
dealer packages, or replacement advice.

## 7. Model human handoff as a local mock

**Decision:** Return a typed local ticket/reference result for explicit handoff
intent and disclose that no external system was contacted.

**Why:** This demonstrates escalation orchestration without implying unavailable
CRM, dealer, email, messaging, appointment, or call-centre integrations.

## 8. Preserve structured capability results in one customer portal

**Decision:** Build one React/Vite/TypeScript ownership workspace around
`POST /assistant/query`. Validate responses at runtime and render separate cards
for maintenance, recommendations, grounded support, mock handoff, and the ML
comparison.

**Why:** Structured results retain capability meaning and make the demo clearer
than a generic chatbot or raw JSON interface.

**Rejected:** Frontend intent routing, flattening every result into prose, Redux,
React Router, or a large UI framework without product need.

## 9. Separate experimental/admin UI from the customer journey

**Decision:** Place the eight-field predictive comparison in a secondary
Technical Preview rather than among primary customer quick actions. Keep
synthetic-data, failed-gate, and non-override disclosures visible.

**Why:** Manual feature entry is an evaluation/demo workflow, not a believable
normal owner interaction. Customer flows should prioritize maintenance,
recommendations, grounded support, and handoff.

## 10. Bootstrap fresh runtimes explicitly and restrict CORS

**Decision:** Use environment-driven SQLite/artifact paths and FastAPI lifespan
startup to create tables, seed idempotently, and reuse/reconstruct the frozen
artifact. Accept only configured exact frontend origins, with no wildcard or
credentials.

**Why:** A fresh container must not rely on a developer machine, while browser
access should remain narrowly configured.

**Rejected:** Committed runtime state, silent prediction changes, large settings
frameworks, permissive wildcard CORS, or unnecessary credentials.

## 11. Ship one production backend Docker image

**Decision:** Use `python:3.13-slim`, runtime-only dependencies, non-root Uvicorn,
a writable `/app/runtime`, build-time MiniLM prefetch, offline Hugging Face
runtime, dynamic `PORT`, and `/health`.

**Why:** Render needs a reproducible image containing source and the controlled
corpus while generating database/artifact state only at runtime.

**Rejected:** Baking local databases/artifacts or secrets into image layers,
using a reload server, or adding Compose/Kubernetes for a single backend.

## 12. Deploy the frontend on Vercel and backend on Render

**Decision:** Host the static Vite frontend on Vercel and the Docker/FastAPI API
on Render, with the backend URL supplied to the frontend and the Vercel origin
allowed explicitly by CORS.

**Why:** This is a small, understandable deployment topology suitable for a
public proof of concept. Render's remote build also validates the Docker image
on a machine where no local Docker-compatible engine was available.

**Trade-off:** The free Render tier may cold-start after inactivity, and SQLite
runtime state remains demo-oriented and may reset with the instance lifecycle
or redeployment rather than acting as durable production storage.

## 13. Use lightweight privacy-conscious JSON observability

**Decision:** Emit standard-library JSON logs for request lifecycle, assistant
routing outcome, runtime bootstrap, readiness, shutdown, and unexpected errors.
Assign or safely reuse `X-Request-ID` and record monotonic duration. Configure
severity with `LOG_LEVEL`.

**Why:** Operational debugging needs correlation and outcome visibility without
heavy monitoring infrastructure or collection of customer content.

**Rejected:** Logging request bodies/messages, predictive inputs, retrieved or
generated content, database records, or secrets; database audit logs; external
log SaaS; Prometheus/Grafana/ELK; OpenTelemetry collectors.
