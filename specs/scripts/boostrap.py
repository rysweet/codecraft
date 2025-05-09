#!/usr/bin/env python
"""
Micro‑Spec · bootstrap_spec_dialog
=================================
**Purpose**  – Provide a stand‑alone helper that bootstraps Markdown specs through an iterative LLM dialog.

**Scope / Responsibilities**
1. Load or create `specs/00_overview.md`.
2. Ask *one* clarifying question at a time (Azure OpenAI, bearer‑token auth).
3. Read the user’s CLI answer.
4. Generate a unified‑diff patch and apply it via a 3‑tier strategy:
   1. Direct unidiff apply.
   2. Smart hunk insertion (context anchoring).
   3. Append diff under marker and auto‑reorder headings.
5. Optional `--reorder` flag alphabetises top‑level headings.

**Guardrails**
* Must use bearer‑token auth (`DefaultAzureCredential`).
* No plaintext API keys committed.
* On patch failure write `.rej` or append marker; never overwrite spec blindly.
* Lint: `ruff`, typecheck: `mypy`, formatter: `black`.  (Handled by CodeCraft guardrail script.)

**Out of scope**
* Fancy diff merge algorithms (3‑way merge, AST‑aware).
* GUI – purely CLI.

**Acceptance tests** (to be scripted later)
* Start with minimal spec ➜ run tool ➜ answer Q ➜ file updated ✔︎
* Simulate bad diff ➜ ensure marker appended & headings reordered ✔︎
* `--reorder` alone reorders H1 blocks alphabetically ✔︎
"""

# ---------------------------------------------------------------------
# bootstrap_spec_dialog.py  (v0.6)
# ---------------------------------------------------------------------
# Iterative helper that refines a Markdown spec via Azure OpenAI.
# Searches for .env in `.codecraft/.env` then repo root.
# ---------------------------------------------------------------------

from __future__ import annotations
import os, sys, pathlib, re
from datetime import datetime
from typing import List
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.panel import Panel
from unidiff import PatchSet, PatchedFile
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

console = Console()

# ────────────────── .env loading ─────────────────────────────────────────
ROOT = pathlib.Path.cwd()
CODECRAFT_ENV = ROOT / ".codecraft" / ".env"
if CODECRAFT_ENV.exists():
    load_dotenv(dotenv_path=CODECRAFT_ENV, override=False)
else:
    fallback_env = find_dotenv(usecwd=True)
    if fallback_env:
        load_dotenv(fallback_env, override=False)

# ────────────────── Azure OpenAI client ──────────────────────────────────
ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
API_VERS   = "2025-03-01-preview"

client = AzureOpenAI(
    azure_endpoint=ENDPOINT,
    api_version=API_VERS,
    azure_ad_token_provider=get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    ),
)

# ────────────────── Paths ────────────────────────────────────────────────
SPEC_PATH = ROOT / "specs" / "00_overview.md"
SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
if not SPEC_PATH.exists():
    SPEC_PATH.write_text("# Rough Sketch\n\n_TODO: describe your idea here._\n")

# ────────────────── LLM prompts ──────────────────────────────────────────
SYS_ASK = (
    "You are a senior PM AI. From the current spec, output exactly ONE clarifying question that moves it toward a shippable overview."
)
SYS_PATCH = (
    "You are an expert editor. Given the user's answer, output a unified git diff that updates the Markdown spec."
)

def ask_llm(messages: List[dict]) -> str:
    return client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        max_completion_tokens=2048,
    ).choices[0].message.content.strip()

# ────────────────── Diff helpers ─────────────────────────────────────────

def _apply_diff(original: List[str], patch: PatchedFile) -> List[str] | None:
    out, idx = [], 0
    try:
        for h in patch:
            while idx < h.source_start - 1:
                out.append(original[idx]); idx += 1
            for line in h:
                if line.is_context or line.is_added:
                    out.append(line.value)
                if not line.is_added:
                    idx += 1
        out.extend(original[idx:])
        return out
    except IndexError:
        return None


def reorder_headings(md_text: str) -> str:
    blocks = re.split(r"(?m)^# (.+)$", md_text)
    intro = blocks[0]
    titled = list(zip(blocks[1::2], blocks[2::2]))
    titled.sort(key=lambda t: t[0].lower())
    return intro + "".join(f"# {h}{b}" for h, b in titled)


def apply_patch_pipeline(spec_path: pathlib.Path, diff_text: str) -> None:
    original = spec_path.read_text().splitlines(keepends=True)
    patchset = PatchSet(diff_text.splitlines(keepends=True))
    if not patchset:
        console.print("[red]❌ Empty diff from LLM"); return
    target = patchset[0]

    # 1️⃣ direct apply
    patched = _apply_diff(original, target)
    if patched:
        spec_path.write_text("".join(patched))
        console.print("[green]✓ patch applied (direct)")
        return

    # 2️⃣ smart insert
    console.print("[yellow]Direct failed → smart insert…")
    smart = original[:]
    for h in target:
        ctx = next((l.value for l in h if l.is_context), None)
        if ctx and ctx in smart:
            smart.insert(smart.index(ctx), *(l.value for l in h if l.is_added))
        else:
            break
    else:  # no break ⇒ success
        spec_path.write_text("".join(smart))
        console.print("[green]✓ patch applied (smart)")
        return

    # 3️⃣ append + reorder
    console.print("[red]Smart insert failed → append diff & reorder headings")
    marker = f"\n<!-- OUT-OF-ORDER PATCH {datetime.utcnow().isoformat()} -->\n"
    spec_path.write_text(spec_path.read_text() + marker + diff_text)
    spec_path.write_text(reorder_headings(spec_path.read_text()))
    console.print("[green]✓ appended & reordered")

# ────────────────── Interactive loop ─────────────────────────────────────

def interactive():
    spec_text = SPEC_PATH.read_text()
    while True:
        question = ask_llm([
            {"role": "system", "content": SYS_ASK},
            {"role": "user", "content": spec_text},
        ])
        console.print(Panel(question, title="Clarifying Question", style="cyan"))
        answer = console.input("[bold green]Your answer (or /done): [/] ")
        if answer.strip().lower() == "/done":
            break
        diff = ask_llm([
            {"role": "system", "content": SYS_PATCH},
            {"role": "user", "content": f"SPEC:\n{spec_text}\nANSWER:\n{answer}"},
        ])
        console.print(Panel(diff, title="Proposed Patch", style="magenta"))
        apply_patch_pipeline(SPEC_PATH, diff)
        spec_text = SPEC_PATH.read_text()

# ────────────────── CLI entry ─────────────────────────────────────────────

def main():
    if "--reorder" in sys.argv:
        SPEC_PATH.write_text(reorder_headings(SPEC_PATH.read_text()))
        console.print("[green]Headings reordered.")
    else:
        interactive()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted")
