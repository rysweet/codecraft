---
title: "P1 · Orchestrator & Feedback Infrastructure"
spec_version: "0.1.0"
last_updated: 2025-05-07
owner: pma
status: draft        # draft | approved | deprecated
phase: 4             # Component Spec
tokens_budget: 8000
parent: 00_overview.md
---

## 1 · Purpose
Run, observe, and course-correct **all** playbook agents (PMA, Decomposer, Coding, DevOps).  
The Orchestrator delivers four guarantees:

1. **Liveness ** – every micro-spec is picked up by exactly one agent instance.
2. **Traceability ** – every action, stdout line, and guardrail result is captured as an event.
3. **Immediate feedback ** – humans see progress (or failures) in real time via chat, GitHub Checks, and a web dashboard.
4. **Self-healing ** – agents that crash or stall are restarted; persistent failures open a backlog ticket automatically.

## 2 · High-level architecture

```mermaid
graph TD
  subgraph Cloud
    ES[CloudEvents<br/>Topic]
    S3[(Artifact Store)]
  end
  subgraph Cluster (k8s)
    ORC[Orchestrator<br/>Deployment]
    SCHED[Task Scheduler]
    ROUTER[Event Router]
    REG[Agent Registry]
    SUP[Agent Supervisor]
    DASH[Feedback UI<br/>(FastAPI + React)]
  end
  ES-->|Publish/Subscribe|ROUTER
  ROUTER-->|Dispatch|SCHED
  SCHED-->|Micro-spec Task|AGENTS[(Agents<br/>(Autogen-core))]
  AGENTS-->|Result / Logs|ES
  SUP-->|Health / Restart|AGENTS
  REG-->|Register / Heartbeat|AGENTS
  ORC-->ES
  ES-->|Snapshots|S3
  ORC-->|REST / WebSocket|DASH
