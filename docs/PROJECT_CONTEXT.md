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

- Acts as the data source for predictive maintenance and recommendation modules.

1. Manual and FAQ Assistant
- Uses Retrieval Augmented Generation (RAG)
- Provides grounded answers with sources

2. Predictive Maintenance
- Uses synthetic vehicle and service data
- Compares rule-based logic with a lightweight ML model

3. Service Recommendations
- Provides explainable maintenance suggestions
- Uses deterministic business rules

4. Escalation Handling
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

High-level flow:

User
↓
React Frontend
↓
FastAPI Backend
↓
Router / Orchestrator
↓
Specialized Modules (RAG, Predictive Maintenance, Recommendation, Escalation)
↓
SQLite Data Layer (Customer Records, Vehicle Records, Service History)

Specialized Modules:

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