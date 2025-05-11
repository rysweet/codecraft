# --- Criticisms & Improvements: Self-Rebuild/Self-Improve ---
| Priority | Feature/Improvement                        | Description                                                                                                    |
|----------|--------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| P0       | Human-in-the-Loop for Self-Edits           | Require user review/approval before overwriting tool code with LLM-generated output.                           |
| P0.1     | Git-Based Versioning & Rollback            | Commit each self-edit to a git branch and allow easy rollback to previous versions.                            |
| P0.2     | Static Analysis & Linting in Self-Improve  | Add linting, type-checking, and static analysis to the self-improvement pipeline.                              |
| P0.3     | Persistent Audit Trail                     | Log all LLM prompts, responses, and diffs to a persistent file for traceability and debugging.                 |
| P1       | Dry-Run & Diff Preview for Self-Rebuild    | Show a diff and require confirmation before applying LLM-generated code changes.                               |
| P2       | Prompt/Spec Synchronization Check          | Detect and surface drift between prompts/spec and actual code; require review of prompt changes.               |
| P3       | Multi-LLM/Agent Abstraction                | Abstract LLM client to support multiple providers and agent architectures.                                     |
| P4       | Fine-Grained Self-Improvement Controls     | Allow targeted or scoped self-improvement (e.g., only update a helper or docstring).                          |
| P5       | Enhanced Observability                     | Provide a dashboard or UI for reviewing self-improvement history, diffs, and LLM interactions.                 |

# --- Observations from Auto-Mode Cat App Spec Generation ---
| Priority | Feature/Improvement                        | Description                                                                                                    |
|----------|--------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| P0       | Initial Spec Scaffolding CLI               | Provide a flag to scaffold a new spec file (title, metadata) for a fresh project before auto-cycles.           |
| P1       | Spec Context Injection                     | Allow user to supply initial spec context or template file to guide first turn, rather than using default overview. |
| P1.1     | Turn-by-Turn Review Mode                    | Add interactive pause and user approval after each auto turn to catch drift earlier.                            |
| P2       | Logging to File                            | Support writing auto-cycle logs to a structured file rather than only console output for later analysis.        |
| P3       | Retry & Backoff on LLM Errors              | Implement retry logic with exponential backoff for ask_llm calls to handle transient API failures gracefully.   |
| P4       | Turn Reduction Based on Convergence        | Allow auto-loop to terminate early when spec changes become minimal, avoiding unnecessary turns.                 |
| P5       | Naming & Metadata in Spec Output           | Ensure generated spec includes clear title, date, version, and unique identifiers for traceability.             |
# Bootstrap Tool Backlog

This backlog prioritizes planned features and improvements for the spec bootstrap tool, focusing on producing high-quality software specifications.

| Priority | Feature                                   | Description                                                                                       |
| -------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------- |
| P0       | Robust Patch Pipeline                     | Improve merge reliability for Markdown using semantic AST-based diff (e.g., remark AST), CRDTs, or operational transforms to target logical sections rather than text lines.  |
| P0.1     | Evaluate AST Libraries                     | Research and compare markdown-it-py, remark, and unified AST diff libraries for suitability.      |
| P0.2     | Prototype AST Diff Mode                    | Implement a proof-of-concept AST-diff application using the chosen library and integrate with `apply_semantic_patch`. |
| P0.3     | Integrate CRDT/OT for Concurrent Edits     | Explore CRDT or operational transform libraries (e.g., Automerge, Yjs) for multi-write scenarios. |
| P1       | Pending Updates Table UX                  | Improve "Pending Updates" section formatting and allow inline editing before LLM re-pass.       |
| P2       | VS Code Extension Integration             | Expose spec refinement panels within the CodeCraft VS Code extension for seamless workflow.       |
| P3       | Multi-LLM Support                         | Abstract out the OpenAI client to allow switching between Azure OpenAI, OpenAI.com, or local LLMs. |
| P4       | Spec Versioning & History Visualization   | Integrate with Neo4j or Git to visualize spec evolution and author contributions over time.       |
| P5       | Customizable Prompt Templates via prompty.ai | Build a UI or CLI wizard to scaffold and manage custom prompt variations.                         |
