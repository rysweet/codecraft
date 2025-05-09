#!/usr/bin/env python
"""
bootstrap_spec_dialog.py  (v0.5)
--------------------------------
Iterative refinement helper for Markdown specs using Azure OpenAI.
Adds a **three‑tier patch pipeline**:
  1. direct apply with unidiff
  2. smart‑insert hunks
  3. append diff + **auto‑reorder headings** to fold the patch in

Run `python bootstrap_spec_dialog.py` for dialog mode or
`python bootstrap_spec_dialog.py --reorder` to reorder headings only.
"""
from __future__ import annotations
import os, sys, pathlib, re
from datetime import datetime
from typing import List
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from unidiff import PatchSet, PatchedFile
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

console = Console()
load_dotenv()

# ── Azure OpenAI client ────────────────────────────────────────────────────
ENDPOINT   = os.environ["AZURE_OPENAI_ENDPOINT"]
DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
API_VERS   = "2025-03-01-preview"

client = AzureOpenAI(
    azure_endpoint=ENDPOINT,
    api_version=API_VERS,
    azure_ad_token_provider=get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    ),
)

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT      = pathlib.Path.cwd()
SPEC_PATH = ROOT / "specs" / "00_overview.md"
SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
if not SPEC_PATH.exists():
    SPEC_PATH.write_text("# Rough Sketch\n\n_TODO: describe your idea here._\n")

# ── LLM prompts ───────────────────────────────────────────────────────────
SYS_ASK = (
    "You are a senior program-manager AI. From the current Markdown spec, "
    "output exactly ONE clarifying question that will move the spec toward a shippable overview."
)
SYS_PATCH = (
    "You are an expert technical editor. Given the user's answer, output a unified "
    "GIT diff that updates the Markdown spec. Do not wrap the diff in markdown fences."
)


def ask_llm(messages: List[dict]) -> str:
    return client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        max_completion_tokens=2048,
    ).choices[0].message.content.strip()

# ── Diff helpers ──────────────────────────────────────────────────────────

def _apply_diff(original: List[str], patch: PatchedFile) -> List[str] | None:
    out, idx = [], 0
    try:
        for hunk in patch:
            while idx < hunk.source_start - 1:
                out.append(original[idx]); idx += 1
            for line in hunk:
                if line.is_context or line.is_added:
                    out.append(line.value)
                if not line.is_added:
                    idx += 1
        out.extend(original[idx:])
        return out
    except IndexError:
        return None


def reorder_headings(md_text: str) -> str:
    """Very naive: alphabetically reorder **top‑level** # headings."""
    blocks = re.split(r"(?m)^# (.+)$", md_text)
    intro = blocks[0]
    titled = list(zip(blocks[1::2], blocks[2::2]))
    titled.sort(key=lambda t: t[0].lower())
    return intro + "".join(f"# {h}{b}" for h, b in titled)


def apply_patch_pipeline(spec_path: pathlib.Path, diff_text: str) -> None:
    original_lines = spec_path.read_text().splitlines(keepends=True)
    patchset = PatchSet(diff_text.splitlines(keepends=True))
    if not patchset:
        console.print("[red]❌ Empty diff from LLM")
        return
    target = patchset[0]

    # 1️⃣ direct apply
    new_lines = _apply_diff(original_lines, target)
    if new_lines:
        spec_path.write_text("".join(new_lines))
        console.print("[green]✓ applied (direct)[/]")
        return

    # 2️⃣ smart insert
    console.print("[yellow]Direct failed → smart insert hunks…[/]")
    smart = original_lines[:]
    inserted = True
    for h in target:
        ctx = next((l.value for l in h if l.is_context), None)
        if ctx and ctx in smart:
            pos = smart.index(ctx)
            smart[pos:pos] = [l.value for l in h if l.is_added]
        else:
            inserted = False
            break
    if inserted:
        spec_path.write_text("".join(smart))
        console.print("[green]✓ applied (smart insert)[/]")
        return

    # 3️⃣ append fallback + reorder
    console.print("[red]Smart insert failed → append diff & reorder headings[/]")
    append_marker = f"\n<!-- OUT-OF-ORDER PATCH {datetime.utcnow().isoformat()} -->\n"
    with spec_path.open("a") as f:
        f.write(append_marker + diff_text)
    spec_path.write_text(reorder_headings(spec_path.read_text()))
    console.print("[green]✓ appended & reordered[/]")

# ───────────────── Interactive loop ──────────────────────────────────────

def interactive():
    spec_text = SPEC_PATH.read_text()
    while True:
        q = ask_llm([
            {"role": "system", "content": SYS_ASK},
            {"role": "user", "content": spec_text},
        ])
        console.print(Panel(q, title="Clarifying Question", style="cyan"))
        ans = console.input("[bold green]Your answer (or /done): [/] ")
        if ans.strip().lower() == "/done":
            break
        diff = ask_llm([
            {"role": "system", "content": SYS_PATCH},
            {"role": "user", "content": f"SPEC:\n{spec_text}\nANSWER:\n{ans}"},
        ])
        console.print(Panel(diff, title="Proposed Patch", style="magenta"))
        apply_patch_pipeline(SPEC_PATH, diff)
        spec_text = SPEC_PATH.read_text()

# ───────────────── CLI entry ─────────────────────────────────────────────

def main():
    if "--reorder" in sys.argv:
        SPEC_PATH.write_text(reorder_headings(SPEC_PATH.read_text()))
        console.print("[green]Headings reordered alphabetically.[/]")
    else:
        interactive()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted.[/]")
