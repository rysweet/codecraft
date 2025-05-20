
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
=======
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
