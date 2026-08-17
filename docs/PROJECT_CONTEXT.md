# Agentic Customer Ownership Copilot

## Overview

Agentic Customer Ownership Copilot is a proof-of-concept AI assistant for automotive customer support.

The system helps vehicle owners understand:
- Vehicle information
- Maintenance requirements
- Service recommendations
- Support documentation
- Escalation options

## Problem Statement

Vehicle owners currently interact with disconnected sources such as:
- Owner manuals
- FAQs
- Service records
- Customer support channels

The system aims to provide a single conversational layer that answers:

"What does my car need, and when?"

## Current Capabilities

0. Data Layer

- SQLite database containing synthetic:
  - Customer records
  - Vehicle information
  - Service history

- Supplies stored vehicle/service data to deterministic maintenance evaluation.
- The experimental ML comparison currently accepts explicit runtime features and
  is not integrated with persistence.

1. Deterministic Maintenance

- Uses a pure, explainable due-status evaluator.
- Uses stored synthetic vehicle and scheduled-service data when requested.
- Remains authoritative for MVP maintenance status.

2. RAG Retrieval
- Uses Retrieval Augmented Generation (RAG)
- Provides confidence-gated grounded answers with source metadata.
- Returns a deterministic insufficient-information response when retrieved
  context is unsupported.

3. Experimental Predictive Maintenance
- Keeps the pure deterministic evaluator authoritative for MVP maintenance status
- Uses a controlled synthetic dataset for an isolated lightweight ML experiment
- Exposes deterministic status and experimental 90-day ML risk side by side
  without producing a hybrid or final decision
- Requires explicit experimental/ML routing intent.
- Does not demonstrate real-world predictive-maintenance accuracy.

4. Escalation Service
- Creates a typed local mock human-handoff result after deterministic routing.
- Does not integrate with a real CRM, dealer, email, or messaging service.

5. Router and Orchestrator

- Classifies a deliberately small set of intents using deterministic rules.
- Treats unsupported and ambiguous requests as explicit outcomes instead of
  silently invoking an arbitrary tool.
- Invokes route-specific tools with only their required context and returns
  structured capability-specific results.
- Exposes the unified typed `POST /assistant/query` entry point while preserving
  the existing direct endpoints.

6. React Frontend

- Uses React, Vite, and TypeScript for one responsive automotive ownership
  dashboard and embedded assistant experience.
- Connects to `POST /assistant/query` through a typed native-fetch client and a
  Vite development proxy.
- Presents authoritative maintenance, grounded support sources, local mock
  handoffs, and experimental predictive comparison results as distinct typed
  experiences rather than raw JSON or generic chat text.
- Includes explicit synthetic-data, failed-gate, non-override, and mock-service
  disclosures wherever those boundaries matter.

Phase 5 frontend work is complete. Observability, Docker, final documentation,
and demo work remain planned for Phase 6.

## Architecture

The implemented FastAPI backend uses a deterministic router followed by an
explicit orchestrator. It is a tool-orchestration architecture, not an
autonomous multi-agent system.

Current application flow:

User
-> Responsive React ownership dashboard and assistant
-> Typed frontend API client and Vite development proxy
-> FastAPI validation and runtime dependencies
-> Deterministic router
-> Explicit orchestrator
-> Existing tools and services
-> Structured response

The routable capabilities are:

1. Authoritative deterministic stored-vehicle maintenance
2. Grounded support/RAG with confidence status and sources
3. Deterministic local mock human escalation/handoff
4. Explicitly experimental predictive-maintenance comparison

The MVP uses no LLM intent classifier, LLM tool calling, LangChain agent,
LangGraph workflow, or autonomous specialized agents. The predictive comparison
cannot override deterministic maintenance and produces no combined, final, or
recommended maintenance status.

Data Layer:
SQLite Database
- Customer Records
- Vehicle Records
- Service History

Stored-vehicle maintenance uses the SQLite data layer. Support/RAG uses the
controlled document corpus. The experimental predictive comparison accepts its
explicit eight-feature input and remains separate from persistence. Mock handoff
creation is local and in-memory.

The unified `POST /assistant/query` endpoint supplements these direct endpoints:

- `GET /health`
- `POST /maintenance/evaluate`
- `GET /vehicles/{vehicle_id}/maintenance`
- `POST /support/query`
- `POST /maintenance/predictive/compare`

The frontend uses the unified endpoint as its primary interaction contract. It
does not recreate routing rules, flatten structured capability results, invent
missing vehicle or experiment inputs, or replace the direct APIs.

## Constraints

- Synthetic/public data only
- No proprietary company information
- Educational proof-of-concept
- Low-cost API usage
- Explainable implementation
- Safety-focused responses

## Development Goal

Build an interview-ready AI application demonstrating:

- Backend development
- RAG systems
- AI tool orchestration
- Machine learning evaluation
- Software engineering practices
