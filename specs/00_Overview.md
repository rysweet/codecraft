---

title: "CodeCraft – Spec‑First Development Platform Overview"
spec\_version: "1.0.0"
last\_updated: 2025-05-08
owner: pma
status: draft
stage: 2                  # 1 = Sketch, 2 = Overview, 3 = Refinement, …
tokens\_budget: 16000
---------------------

## 1 · Vision

**CodeCraft** is a local‑first, agent‑driven companion for senior developers and PMs.
Running entirely as a **VS Code extension**, it lets you stay in flow while designing, coding, and maintaining software through a spec‑first approach.

* **One‑click startup.** Activating the extension boots a local Docker stack (orchestration router, scheduler, Autogen‑core agent pool, Neo4j, MCP servers) and opens three in‑editor panels: **Chat**, **Graph Explorer**, **Guardrail Dashboard**.
* **Remote LLMs via Azure OpenAI.** All inference is proxied through a thin Python API head so the extension only speaks local HTTP/WS.
* **Self‑improving loop.** Error → fix cycles trigger spec/backlog patches and rich commit messages on a feature branch—continuous learning baked in.
* **All edits live in VS Code.** No extra web editors; the extension leverages VS Code’s native diff and file system.

---

## 2 · Goals for Initial Release

| Priority | Goal                           | Notes                                                                                                                       |
| -------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| L0       | **VS Code extension panels**   | ① Chat (Dialog Agent), ② Graph Explorer, ③ Guardrail Dashboard.                                                             |
| L0       | **Interactive dialog mode**    | Proactive suggestions; periodic summaries stored in **MCP Neo4j Memory** service.                                           |
| L0       | **Code‑understanding service** | Neo4j + MCP Cypher server; graph built by **Blarify** (Tree‑sitter based). Minimum language support: **Python, JS/TS, C#**. |
| L0       | **Guardrail‑driven agents**    | Autogen‑core Coding Agents enforce tests/format/docs through a local CI shim.                                               |
| L0       | **Self‑improving loop**        | Trace‑Watcher Agent patches specs/backlog and pushes PRs with descriptive messages.                                         |

*(Future cloud/Kubernetes scale‑out is intentionally deferred.)*

---

## 3 · Core Components

1. **Spec Repository** – Git repo: Markdown specs, prompts, backlog, docs, source.
2. **Dialog Agent** – Runs inside Autogen‑core; provides chat Q\&A panel.
3. **Trace‑Watcher Agent** – Listens to Error‑Trace events; patches specs/backlog.
4. **Program‑Manager Agent (PMA)** – Batch spec governance when dialog mode is off.
5. **Decomposer Agent** – Breaks component specs into micro‑specs.
6. **Coding Agents** – Write code under guardrails.
7. **DevOps Agent** – Local packaging and CI harness.
8. **Local Orchestrator** – Scheduler + CloudEvents router (Python FastAPI).
9. **Code‑Understanding Service** – **Neo4j** behind **MCP Cypher** server; graph built by **Blarify** workers.
10. **MCP Memory Server** – Conversation store (replaces SQLite); periodical summary nodes persisted.
11. **CodeCraft VS Code Extension** – UI panels + CLI wrapper.
12. **CodeCraft CLI** – `up/down/status/dialog` commands for headless/CI mode.
13. **LLM Gateway** – Azure OpenAI wrapper (retry, logging, cost tracking).

---

## 4 · Conversation Persistence

* **Verbatim chat** is kept in transient memory (MCP Memory).
* Every *N* turns (configurable), the Dialog Agent writes a **Summary node** to MCP Memory (`(:ConversationSummary { decisions, timestamp })`).
* Summaries are surfaced in the Chat panel and can be inserted into commit messages.

---

## 5 · Code‑Understanding Service Details

| Aspect                | Decision                                                                                                               |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Parser/Indexer**    | **Blarify** (Tree‑sitter) running in a Linux container.                                                                |
| **Languages**         | **Python, JavaScript/TypeScript, C#** (plus any others Blarify supports).                                              |
| **Graph backend**     | **Neo4j** with the **mcp‑neo4j‑cypher** server.                                                                        |
| **Labels**            | `File`, `AST`, `Symbol`, `Spec`, `Doc`, `Embedding` (hash & language as node props).                                   |
| **Relationships**     | Dynamic; evolves with code. Core ones: `CONTAINS`, `DEFINED_IN`, `IMPLEMENTS`, `EMBEDS`.                               |
| **Embeddings**        | Single Azure OpenAI model (`text‑embedding‑3‑small`).                                                                  |
| **Schema versioning** | TODO – evaluate Neo4j best practices (option: `schema_version` prop on Graph metadata node).                           |
| **Query surfaces**    | MCP Cypher, plus thin Python wrapper. Planned REST endpoints: `/symbol/{fqdn}`, `/embedding/query`, `/graph/subgraph`. |
| **Performance**       | Functionality first; no strict latency SLA in v1.                                                                      |

---

## 6 · Dialog & Autonomy Lifecycle

1. **Start Dialog** – *Command Palette ▶ CodeCraft: Start Dialog* (or `codecraft cli dialog start`).
2. **Proactive Q\&A** – Dialog Agent guides spec updates; writes patches via editor‑tool diff.
3. **Go Autonomous** – *Command Palette ▶ CodeCraft: Go Autonomous* (or `codecraft cli go-autonomous`).
4. **Trace‑Watcher** – Runs separate Autogen‑core agent, commits spec/backlog fixes on its own branch.
5. **Resume Dialog** – Agent renders a summary of autonomous commits before re‑entering Q\&A.

---

## 7 · Development & Deployment Modes

| Mode                  | How it runs                                           | External deps    |
| --------------------- | ----------------------------------------------------- | ---------------- |
| **VS Code Extension** | Boots Docker stack via CLI; exposes HTTP/WS to panels | Azure OpenAI key |
| **CI (GitHub)**       | CLI in headless mode with Docker‑in‑Docker            | Secrets mounted  |

---

## 8 · Stages & Deliverables

| Stage | Name              | Deliverables                                                                                                  | Owner        |
| ----- | ----------------- | ------------------------------------------------------------------------------------------------------------- | ------------ |
| S1    | Rough Sketch      | `sketch.md`                                                                                                   | Stakeholder  |
| S2    | **This overview** | `00_overview.md`                                                                                              | PMA          |
| S3    | Refinement Loop   | PR patches                                                                                                    | PMA          |
| S4    | Component Specs   | `P0_agents`, `P1_orchestrator`, `P2_graph_service`, `P3_vscode_extension`, `P4_llm_gateway`, `P5_dialog_mode` | PMA          |
| S5    | Micro‑Specs       | `NN_step.md` per component                                                                                    | Decomposer   |
| S6    | Backlog & Review  | `backlog.md`, `review.md`                                                                                     | PMA          |
| S7    | Code Generation   | Source + tests + docs                                                                                         | Coding Agent |
| S8    | Local CI Harness  | Guardrail script + GH Action                                                                                  | DevOps Agent |

---

## 9 · Upcoming Component Specs

| ID                        | Folder                       | Brief                                     |
| ------------------------- | ---------------------------- | ----------------------------------------- |
| **P0\_agents**            | `specs/P0_agents/`           | Agent runtime, guardrails (Autogen‑core). |
| **P1\_orchestrator**      | `specs/P1_orchestrator/`     | Local scheduler & CloudEvents router.     |
| **P2\_graph\_service**    | `specs/P2_graph_service/`    | Neo4j + MCP servers + Blarify workers.    |
| **P3\_vscode\_extension** | `specs/P3_vscode_extension/` | Extension panels & commands.              |
| **P4\_llm\_gateway**      | `specs/P4_llm_gateway/`      | Azure OpenAI proxy, retry, cost.          |
| **P5\_dialog\_mode**      | `specs/P5_dialog_mode/`      | Dialog & Trace‑Watcher agents.            |

---

## 10 · Open Questions

1. **Schema versioning approach** – research Neo4j best practice.
2. **Graph visualizer library** – D3.js vs Vis.js vs Cytoscape for VS Code WebView.
3. **CLI plugin architecture** – yargs vs Typer?  (Typer excluded earlier, reconsider?)
