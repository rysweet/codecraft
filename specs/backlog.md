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
