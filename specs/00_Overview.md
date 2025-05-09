---

title: "CodeCraft – Spec‑First Development Platform Overview"
spec\_version: "1.3.0"
last\_updated: 2025-05-08
owner: pma
status: draft
stage: 2                  # 1 = Sketch, 2 = Overview, 3 = Refinement …
tokens\_budget: 16000
---------------------

# 1 · Vision

**CodeCraft** is a **local‑first, agent‑driven companion** that keeps senior developers and PMs in flow while they design, generate, and maintain software via a spec‑first methodology. It ships as a **VS Code extension** that spins up a local stack, surfaces chat‑based workflow guidance, and continually improves its own specs.

---

# 2 · Initial‑Release Goals (Level 0)

| Goal                           | Notes                                                                                         |
| ------------------------------ | --------------------------------------------------------------------------------------------- |
| **VS Code extension panels**   | ① Chat (Dialog Agent)  ② Graph Explorer  ③ Guardrail Dashboard                                |
| **Interactive dialog mode**    | Proactive suggestions; periodic conversation summaries in **MCP Neo4j Memory**                |
| **Code‑understanding service** | Neo4j + MCP Cypher; graph built by **Blarify** (Tree‑sitter). Languages ≥ Python · JS/TS · C# |
| **Guardrail‑driven agents**    | Autogen‑core **Coding‑Agent pairs** enforce tests/format/docs via local CI shim               |
| **Self‑improving loop**        | Trace‑Watcher Agent patches specs/backlog and opens PRs with descriptive commits              |

---

# 3 · Core Components

1. **Spec Repository** — Markdown specs, prompts, backlog, docs, source in Git
2. **Dialog Agent** — Chat Q\&A; patches specs live
3. **Trace‑Watcher Agent** — Observes Error‑Trace events; patches specs/backlog
4. **Program‑Manager Agent (PMA)** — Batch spec governance
5. **Decomposer Agent** — Splits component specs into micro‑specs
6. **Coding‑Agent Pairs** — Dev + Review agent per micro‑spec
7. **DevOps Agent** — Local packaging & CI harness
8. **Local Orchestrator** — Uses Autogen‑core’s in‑process router (no external bus)
9. **Code‑Understanding Service** — Neo4j + MCP Cypher populated by Blarify
10. **MCP Memory Server** — Hierarchical agent memory (task, episodic, whiteboard)
11. **CodeCraft Extension** — VS Code UI panels + CLI wrapper
12. **CodeCraft CLI** — `codecraft <verb>` commands for headless / CI
13. **LLM Gateway** — Azure OpenAI proxy with retry, logging, cost tracking

### 3.1 Coding‑Agent Pair Rules

| Rule                              | Behaviour                                                                                                      |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Pair lifecycle**                | Dev + Review spawn together per micro‑spec; share context; terminate together.                                 |
| **Concurrency**                   | Config `pairs=N` (default **10**); Orchestrator spawns ≤ N pairs concurrently.                                 |
| **Guardrail enforcement**         | Review runs `guardrail_check.py` after every Dev change; blocks merge on failure.                              |
| **Escalation flow**               | After 3 failed retries Review triggers a reflection prompt; on 4th failure logs backlog entry + VS Code toast. |
| **No mocks in integration tests** | Review greps `tests/integration` for `unittest.mock` / `pytest‑mock`.                                          |
| **Pair chat**                     | Logged to MCP Memory for summarisation.                                                                        |

### 3.2 Runtime & Concurrency Decisions

* **Process model** — One Docker container per agent *type* (async tasks inside).
* **Task state** — JSON files in `.codecraft/state/task‑<id>.json`; re‑queued on restart if unfinished.
* **Secrets & auth** — `.env‑template` placeholders; prefer Azure AD bearer tokens (`DefaultAzureCredential`) or Key Vault. Plain keys fallback.
* **Logs** — Structured JSON in `.codecraft/logs/YYYYMMDD/`; WS streamed; auto‑prune 30 days.
* **Python** — Latest stable (currently 3.12).
* **Sandbox** — Each micro‑spec runs in a disposable job container (workspace ro bind‑mount).

### 3.3 Agent Memory Model (MCP Neo4j Memory)

| Layer          | Node label        | Purpose                                    |
| -------------- | ----------------- | ------------------------------------------ |
| **Task**       | `:TaskMemory`     | Current micro‑spec notes & next steps      |
| **Episodic**   | `:EpisodicMemory` | Summaries & long‑term decisions            |
| **Whiteboard** | `:Whiteboard`     | Shared goals, bullet status, task division |

### 3.4 Coding‑Agent Implementation Abstraction

`CodingAgentProvider` interface allows plugging in **Claude Code CLI**, **OpenAI Codex CLI**, **SWE‑agent CLI**, etc. Providers register via entry‑points and are selected in `.codecraft/config.toml`.

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

1. **Schema versioning** – settle on Neo4j strategy and encode in metadata node
2. **Graph visualiser library** – choose D3.js vs Vis.js vs Cytoscape for VS Code WebView
3. **CLI plugin architecture** – pick Click/Typer/Argh or custom modular CLI
