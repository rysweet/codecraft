---

title: "CodeCraft – Spec‑First Development Platform Overview"
spec\_version: "1.2.0"
last\_updated: 2025-05-08
owner: pma
status: draft
stage: 2                  # 1 = Sketch, 2 = Overview, 3 = Refinement …
tokens\_budget: 16000
---------------------

# 1 · Vision

**CodeCraft** is a **local‑first, agent‑driven companion** that helps senior developers and PMs stay in flow while designing, generating, and maintaining software via a spec‑first methodology. It ships as a **VS Code extension** that spins up a local stack, surfaces chat‑based workflow guidance, and evolves its own specs as it works.

---

# 2 · Initial‑Release Goals (Level 0)

| Goal                           | Notes                                                                                      |
| ------------------------------ | ------------------------------------------------------------------------------------------ |
| **VS Code extension panels**   | ① Chat (Dialog Agent)  ② Graph Explorer  ③ Guardrail Dashboard                             |
| **Interactive dialog mode**    | Proactive suggestions; periodic conversation summaries stored in **MCP Neo4j Memory**      |
| **Code‑understanding service** | Neo4j + MCP Cypher; graph built by **Blarify** (Tree‑sitter). Languages: Python, JS/TS, C# |
| **Guardrail‑driven agents**    | Autogen‑core Coding‑Agent *pairs* enforce tests/format/docs through a local CI shim        |
| **Self‑improving loop**        | Trace‑Watcher Agent patches specs/backlog and pushes PRs with descriptive commit messages  |

*(Cloud/Kubernetes scale‑out intentionally deferred.)*

---

# 3 · Core Components

1. **Spec Repository** — Markdown specs, prompts, backlog, docs, source in Git
2. **Dialog Agent** — Q\&A in Chat panel; patches specs live
3. **Trace‑Watcher Agent** — Observes Error‑Trace events; patches specs/backlog
4. **Program‑Manager Agent (PMA)** — Batch spec governance when dialog is off
5. **Decomposer Agent** — Breaks component specs into micro‑specs
6. **Coding‑Agent Pairs** — Dev Agent + Review Agent for each assigned micro‑spec
7. **DevOps Agent** — Local packaging and CI harness
8. **Local Orchestrator** — Scheduler + CloudEvents router (Python FastAPI)
9. **Code‑Understanding Service** — Neo4j + MCP Cypher, populated by Blarify workers
10. **MCP Memory Server** — Conversation store (replaces SQLite)
11. **CodeCraft Extension** — VS Code UI panels + CLI wrapper
12. **CodeCraft CLI** — `codecraft <verb>` commands for headless/CI mode
13. **LLM Gateway** — Azure OpenAI proxy with retry, logging, cost tracking

### 3.1 Coding‑Agent Pair Rules

| Rule                              | Behaviour                                                                                                                             |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Pair lifecycle**                | *Dev* + *Review* Agents spawn together per micro‑spec; share context; terminate together.                                             |
| **Concurrency**                   | Config flag `pairs=N` (default **10**). Orchestrator schedules at most N concurrent micro‑specs.                                      |
| **Guardrail enforcement**         | Review Agent runs `guardrail_check.py` after every change; blocks merge on failure.                                                   |
| **Escalation flow**               | After three failed retries, Review Agent triggers a self‑reflection prompt, and on fourth failure logs backlog entry + VS Code toast. |
| **No mocks in integration tests** | Review Agent greps `tests/integration` for `unittest.mock` / `pytest‑mock`.                                                           |
| **Pair chat**                     | Logged to MCP Memory for later summarisation.                                                                                         |

### 3.2 Runtime & Concurrency Decisions

* **Process model** — **One container per agent type** (internal async tasks for each pair).
* **Secrets** — Azure keys via env‑vars loaded from `.codecraft/.env` (VS Code Secret Storage optional later).
* **Logs** — Structured JSON; Orchestrator streams via WebSocket to dashboard.
* **Python** — Base image pins **Python 3.11**.
* **Sandbox** — Dev Agent executes tests/lint inside disposable job containers.

---

# 4 · CLI & Extension UX

| Topic               | Decision                                                             |
| ------------------- | -------------------------------------------------------------------- |
| **Namespace**       | Single binary: `codecraft <verb>` (e.g., `codecraft up`)             |
| **Workspace model** | Stack runs in current workspace; per‑repo config in `.codecraft/`    |
| **CLI output**      | Rich table output; `--json` flag for machine‑readable                |
| **Chat sessions**   | Tabbed chats in extension; CLI lists/opens by index                  |
| **Graph Explorer**  | Auto‑expand until < 1 000 nodes; click to expand further             |
| **Dashboard**       | Snippet from `status.md`, live agent roster, session stats (WS push) |
| **Palette entries** | At minimum Start Dialog & Go Autonomous (others TBD)                 |
| **Keybindings**     | Defer; choose sensible VS Code defaults                              |

---

# 5 · Dialog & Autonomy Lifecycle

1. **Start Dialog** → *Command Palette ▶ CodeCraft: Start Dialog* or `codecraft dialog start`
2. **Proactive Q\&A** → Dialog Agent guides spec updates; writes diff‑style patches
3. **Go Autonomous** → *Command Palette ▶ CodeCraft: Go Autonomous* or `codecraft go-autonomous`
4. **Trace‑Watcher Phase** → Commits spec/backlog fixes on its own branch
5. **Resume Dialog** → Shows autonomous summary, continues Q\&A

Conversation data: verbatim turns are transient; every *N* turns a `ConversationSummary` node is persisted to MCP Memory.

---

# 6 · Code‑Understanding Service

| Aspect                | Decision                                                                                                          |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Indexer**           | **Blarify** (Tree‑sitter) in Linux container                                                                      |
| **Languages**         | Python, JS/TS, C# (plus any extras Blarify supports)                                                              |
| **Backend**           | **Neo4j** via **mcp‑neo4j‑cypher** server                                                                         |
| **Nodes**             | `File`, `AST`, `Symbol`, `Spec`, `Doc`, `Embedding` (props: hash, language)                                       |
| **Relationships**     | Dynamic; starts with `CONTAINS`, `DEFINED_IN`, `IMPLEMENTS`, `EMBEDS`                                             |
| **Embeddings**        | Azure OpenAI `text‑embedding‑3‑small` for code & docs                                                             |
| **Schema versioning** | **TODO** – decide on Neo4j best‑practice (e.g., metadata node)                                                    |
| **API**               | MCP Cypher + thin Python wrapper; planned REST endpoints: `/symbol/{fqdn}`, `/embedding/query`, `/graph/subgraph` |

---

# 7 · Development & Deployment Modes

| Mode                  | How it runs                                   | External deps    |
| --------------------- | --------------------------------------------- | ---------------- |
| **VS Code Extension** | Boots Docker stack via CLI; panels in WebView | Azure OpenAI key |
| **CI (GitHub)**       | CLI headless with Docker‑in‑Docker            | Secrets mounted  |

---

# 8 · Stages & Deliverables

| Stage | Name              | Deliverables                                                                                                  | Owner        |
| ----- | ----------------- | ------------------------------------------------------------------------------------------------------------- | ------------ |
| S1    | Rough Sketch      | `sketch.md`                                                                                                   | Stakeholder  |
| S2    | **This overview** | `00_overview.md`                                                                                              | PMA          |
| S3    | Refinement Loop   | PR patches                                                                                                    | PMA          |
| S4    | Component Specs   | `01_agents`, `02_orchestrator`, `03_graph_service`, `04_vscode_extension`, `05_llm_gateway`, `06_dialog_mode` | PMA          |
| S5    | Micro‑Specs       | `NN_step.md` per component                                                                                    | Decomposer   |
| S6    | Backlog & Review  | `backlog.md`, `review.md`                                                                                     | PMA          |
| S7    | Code Generation   | Source + tests + docs                                                                                         | Coding Agent |
| S8    | Local CI Harness  | Guardrail script + GH Action                                                                                  | DevOps Agent |

---

# 9 · Upcoming Component Specs

| ID                        | Folder                       | Brief                                     |
| ------------------------- | ---------------------------- | ----------------------------------------- |
| **01\_agents**            | `specs/01_agents/`           | Autogen‑core runtime, guardrails          |
| **02\_orchestrator**      | `specs/02_orchestrator/`     | Local scheduler & CloudEvents router      |
| **03\_graph\_service**    | `specs/03_graph_service/`    | Neo4j + MCP servers + Blarify workers     |
| **04\_vscode\_extension** | `specs/04_vscode_extension/` | Extension activation, panels, CLI wrapper |
| **05\_llm\_gateway**      | `specs/05_llm_gateway/`      | Azure OpenAI proxy, retry, cost tracking  |
| **06\_dialog\_mode**      | `specs/06_dialog_mode/`      | Dialog & Trace‑Watcher agents             |

---

# 10 · Open Questions

1. **Schema versioning** – settle on Neo4
