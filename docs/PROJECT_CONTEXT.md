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

## Core Capabilities

The MVP includes:
0. Data Layer

- SQLite database containing synthetic:
  - Customer records
  - Vehicle information
  - Service history

- Acts as the data source for predictive maintenance and recommendation services.

1. RAG Retrieval
- Uses Retrieval Augmented Generation (RAG)
- Provides grounded answers with sources

2. Predictive Maintenance Service
- Uses synthetic vehicle and service-history data
- Estimates service due status using rule-based logic and a lightweight ML experiment
- Evaluates whether the ML approach provides value over the baseline

3. Recommendation Engine
- Provides explainable maintenance suggestions
- Uses deterministic business rules

4. Escalation Service
- Creates mock support tickets for:
  - Safety concerns
  - Customer dissatisfaction
  - Unsupported questions

5. Observability
Tracks:
- Requests
- Routing decisions
- Latency
- Errors
- Model usage when available

## Architecture

The FastAPI backend uses a central router/orchestrator to select and invoke tools and services. These capabilities are not autonomous specialized agents.

High-level flow:

User
↓
React Frontend
↓
FastAPI Backend
↓
Router / Orchestrator
↓
Tools and Services
↓
Response Generation

Data Layer:
SQLite Database
- Customer Records
- Vehicle Records
- Service History

Tools use the data layer when required:

- RAG Retrieval
- Predictive Maintenance
- Recommendation Engine
- Escalation Service

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
