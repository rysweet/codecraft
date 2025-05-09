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

| Aspect                | Decision                                                                                                                                                                                            |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Indexer**           | **Blarify** (Tree‑sitter) in Linux container                                                                                                                                                        |
| **Languages**         | Python, JS/TS, C# (plus any extras Blarify supports)                                                                                                                                                |
| **Backend**           | **Neo4j** via **mcp‑neo4j‑cypher** server                                                                                                                                                           |
| **Nodes**             | `File`, `AST`, `Symbol`, `Spec`, `Doc`, `Embedding` (props: hash, language)                                                                                                                         |
| **Relationships**     | Dynamic; starts with `CONTAINS`, `DEFINED_IN`, `IMPLEMENTS`, `EMBEDS`                                                                                                                               |
| **Embeddings**        | Azure OpenAI `text‑embedding‑3‑small` for code & docs                                                                                                                                               |
| **Schema versioning** | Meta‑node strategy: one `(:GraphMeta {schema_version:"1.0"})` node and chained `(:SchemaChange {version, date, description})` nodes capturing each migration; edge labels expected to remain stable |
| **API**               | MCP Cypher + thin Python wrapper; planned REST endpoints: `/symbol/{fqdn}`, `/embedding/query`, `/graph/subgraph`                                                                                   |

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

---

title: "CodeCraft – Spec‑First Development Platform Overview"
spec\_version: "2.1.0"
last\_updated: 2025‑05‑09
owner: pma
status: draft
stage: 2        # 1 = Sketch, 2 = Overview, 3 = Refinement …
tokens\_budget: 16000
---------------------

# 1. Why CodeCraft?

Traditional project templates grow stale; ad‑hoc chats vanish. **CodeCraft** replaces both with a living Markdown corpus that evolves every time a requirement clarifies or a test fails. The platform embeds itself in VS Code, pairs large‑language‑model agents with guard‑rail scripts, and guarantees that *the spec is the single source of truth*—never an after‑thought.

# 2. Methodology at a Glance (“CodeCraft Cycle”)

| Phase  | Output                             | Done‑when                                                           | Primary Agent |
| ------ | ---------------------------------- | ------------------------------------------------------------------- | ------------- |
| **P0** | *Rough Sketch* (`sketch.md`)       | Stakeholder says “yes”                                              | Dialog Agent  |
| **P1** | *Overview Spec* (`00_overview.md`) | All top‑level sections filled                                       | PMA           |
| **P2** | *Component Specs* (`01_*.md`)      | Each component has responsibilities, architecture, acceptance tests | PMA           |
| **P3** | *Micro‑Specs* (`01_*/NN_step.md`)  | ≤ 8 k tokens & One‑Shot generation section                          | Decomposer    |
| **P4** | *Source + Tests*                   | `ruff`, `black`, `mypy`, `pytest` green                             | Coding Pairs  |
| **P5** | *Backlog + Review*                 | 0 warnings from consistency script                                  | Trace‑Watcher |

*The cycle repeats every time the user clicks **“Go Autonomous”** or when a build breaks.*

# 3. Runtime Topology

```
┌─ VS Code Extension ─────────────────────────────────────────────┐
│ Chat Panel  Graph Explorer  Guardrail Dashboard               │
└────────────────────────────────────────────────────────────────┘
            │ WebView WS/HTTP
┌───────────────────────────── docker compose ───────────────────┐
│  Orchestrator (FastAPI)   Neo4j + MCP         LLM Gateway      │
│  ├─ Dialog Agent          ├─ GraphMeta node   ├─ Azure OpenAI  │
│  ├─ Decomposer Agent      └─ …                └─ Cost tracker  │
│  └─ Dev/Review Pair(s) –> job container(s) → ruff/mypy/tests   │
└────────────────────────────────────────────────────────────────┘
```

* One container per **agent type**; Dev/Review pairs run as asyncio tasks.
* Each compile/test run happens in a throw‑away **job container** (workspace mounted read‑only, working copy copied into `/work`).
* The Orchestrator stores a JSON **Task Ledger** per active micro‑spec in `.codecraft/state/` so it can replay after a crash.

# 4. Persistent Knowledge

The platform persistently links **spec → code → runtime artefacts** so that every agent query—and every human click in the GUI—resolves to a single canonical node in the graph.

## 4.1 Neo4j Code‑Understanding Graph

* **Ingestion worker** – Each Git commit triggers a Blarify run inside `ingester` container: Tree‑sitter parses files, extracts symbols, emits Cypher batches.
* **Core labels**
  `(:File {path, lang, hash})`
  `(:AST {root_id})`
  `(:Symbol {fqdn, kind})`
  `(:Spec {path, heading})`
  `(:Embedding {model, vector})`
* **Edges**
  `(:File)‑[:CONTAINS]→(:AST)`
  `(:AST)‑[:BINDS]→(:Symbol)`
  `(:Spec)‑[:REFS]→(:Symbol)`
  `(:Embedding)‑[:OF]→(:File|:Symbol)`
* **Query surfaces** – MCP Cypher plus REST helper endpoints
  `/symbol/{fqdn}` → JSON with definition, references
  `/graph/subgraph?node=ID&depth=N` → pruned neighbourhood for Graph Explorer.
* **Schema evolution** – `(:GraphMeta {schema_version})` holds the active version; each migration appends a `(:SchemaChange)` node with Cypher patchfile path and SHA.

## 4.2 Agent Memory (MCP)

`TaskMemory` gives agents short‑term focus; `EpisodicMemory` captures durable insights; a shared `Whiteboard` tracks goal bullets and work split.

---

# 5. VS Code Extension Internals

The extension is implemented in **TypeScript + React** (Vite build) and loads as a VS Code WebView.

### 5.1 Panels

1. **Chat Panel** – powered by shadcn/ui Chat component; streams questions/answers via WebSocket. Supports `/search` slash‑command to invoke a web search LLM tool.
2. **Graph Explorer** – Embeds `3d-force-graph` with custom Neo4j Cypher adapter; auto‑loads the whiteboard subgraph on start and enforces the 1 000‑node budget.
3. **Guardrail Dashboard** – Displays live JSON log stream with status bars per agent, recent errors, and cost tracker for Azure OpenAI usage.

### 5.2 Extension Runtime

* **Activation** – triggers `codecraft up`; waits on health‑check endpoint before opening panels.
* **Command Palette**
  `CodeCraft: Start Dialog`
  `CodeCraft: Go Autonomous`
  `CodeCraft: Export Specs` (ZIPs `specs/` to downloads).
* **Secret Storage** – If `.codecraft/.env` lacks an endpoint, the extension prompts for one and stores it in VS Code’s Secret Storage API.
* **Plugin Host** – Loads additional Typer CLI plugins and surfaces them as extra palette commands.

---

# 6. Agents in Detail

## 5.1 Program‑Manager Agent (PMA)

*Rewrites any terse patch into narrative prose plus clarifying bullets.* Enforces active voice, parallel heading depth, and a single tense.

## 5.2 Dialog Agent

* One‑question‑at‑a‑time policy.
* Can hand off to **Architect Agent** for `AUTO_TURNS` cycles; pauses for the user.
* Stores conversation summaries in `:EpisodicMemory` every N turns.

## 5.3 Architect Agent

*Expert in elegant, operable designs.* Answers clearly; may emit `SEARCH: foo` to trigger a web lookup (future hook).

## 5.4 Coding‑Agent Pair

* Dev Agent implements.
* Review Agent blocks until guardrails pass, no mocks in `tests/integration/`, docs updated.
* Reflection prompt after 3 guardrail failures → backlog ticket on 4th.

## 5.5 Trace‑Watcher Agent

Listens to build events. On a recovered error it:

1. Adds a `SchemaChange` or spec patch.
2. Updates `backlog.md`.
3. Pushes a PR titled `refactor(spec): forbid {error‑class}`.

# 6. Extension & CLI Experience

* `codecraft up|down|status` – manage local stack.
* Chat panel → Q\&A; *Graph Explorer* powered by **`3d-force-graph`** (auto‑expand ≤ 1 000 nodes).
* Guardrail Dashboard streams JSON logs; green/red bars per agent.
* `codecraft dialog start` | `codecraft go-autonomous` | `codecraft logs [agent]` | `codecraft export-specs`.
* CLI plugins discovered via Typer entry‑points (`codecraft‑plugin‑*`).

# 7. Development & Deployment Modes

| Mode               | Start cmd      | Containers                            | External       | Notes            |
| ------------------ | -------------- | ------------------------------------- | -------------- | ---------------- |
| **Local**          | `codecraft up` | Orchestrator, Agents, Neo4j, MCP, GUI | Azure OpenAI   | Default workflow |
| **CI**             | GitHub Action  | Same via DinD                         | GitHub Secrets | PR check         |
| **Cloud (future)** | Helm chart     | Split into micro‑services             | NATS, Redis    | Milestone 1      |

# 8. Road‑map (high level)

* **M0 (Apr 2025)** – Local extension, self‑improving loop.
* **M1 (Q3 2025)** – NATS JetStream, multi‑node.
* **M2 (2026)** – Cloud work‑space pooling.

# 9. Glossary

*Micro‑Spec, Guardrail, SchemaChange* – see Appendix B.

# Appendix A – Narrative Commit Message Template

```
refactor(spec): tighten type hints for DataLoader

Context  : mypy error E501 observed in job‑34
Change   : added Generic[T] to DataLoader.__init__
Spec     : 01_agents/02_typing.md updated
Guardrail: type‑check now green
```
