#!/usr/bin/env python
"""
bootstrap_spec_dialog.py  (v0.4)
--------------------------------
Interactive helper that iteratively refines a Markdown spec via Azure OpenAI.

Workflow
========
1. Load (or create) `specs/00_overview.md`.
2. Ask the LLM one clarifying question at a time.
3. Read user's answer from stdin.
4. Ask the LLM for a unified diff patch.
5. Apply the patch with a three‑tier pipeline:
   • direct apply   → success ✅
   • smart‑insert   → context‑line anchoring ✅
   • append fallback → writes OUT‑OF‑ORDER patch 🚧
6. Loop until user types `/done`.

Optional:
    python bootstrap_spec_dialog.py --reorder
reorders top‑level # headings alphabetically.

Prereqs
=======
    pip install openai azure-identity python-dotenv rich unidiff

Environment
===========
    AZURE_OPENAI_ENDPOINT   # e.g. https://my-oai.openai.azure.com
    AZURE_OPENAI_DEPLOYMENT # deployment name (defaults gpt-4o)
"""
from __future__ import annotations
import os, sys, pathlib, shutil, re
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

# ───────────────── Azure OpenAI client ────────────────────────────────────
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

# ───────────────── Paths ─────────────────────────────────────────────────
ROOT       = pathlib.Path.cwd()
SPEC_PATH  = ROOT / "specs" / "00_overview.md"
SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
if not SPEC_PATH.exists():
    SPEC_PATH.write_text("# Rough Sketch\n\n_TODO: describe your idea here._\n")

# ───────────────── Prompts ───────────────────────────────────────────────
SYS_ASK = (
    "You are a senior program-manager AI. From the current Markdown spec, "
    "output exactly ONE clarifying question that will move the spec toward a shippable overview."
)
SYS_PATCH = (
    "You are an expert technical editor. Given the user's answer, output a unified "
    "GIT diff that updates the Markdown spec. Do not wrap the diff in markdown fences."
)

def ask_llm(messages: List[dict], **params) -> str:
    return client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        max_completion_tokens=2048,
        **params,
    ).choices[0].message.content.strip()

# ───────────────── Diff helpers ──────────────────────────────────────────

def _apply_diff(original_lines: List[str], patch: PatchedFile) -> List[str] | None:
    """Return new lines or None if hunk mismatch."""
    out, idx = [], 0
    try:
        for h in patch:
            while idx < h.source_start - 1:
                out.append(original_lines[idx]); idx += 1
            for line in h:
                if line.is_context or line.is_added:
                    out.append(line.value)
                if not line.is_added:
                    idx += 1
        out.extend(original_lines[idx:])
        return out
    except IndexError:
        return None


def apply_patch_pipeline(spec_path: pathlib.Path, diff_text: str) -> bool:
    """Three‑tier patch strategy: direct → smart‑insert → append fallback."""
    original = spec_path.read_text().splitlines(keepends=True)
    patchset = PatchSet(diff_text.splitlines(keepends=True))
    if not patchset:
        console.print("[red]❌ Empty diff from LLM[/]")
        return False
    target   = patchset[0]

    # 1️⃣ direct apply
    new_lines = _apply_diff(original, target)
    if new_lines:
        spec_path.write_text("".join(new_lines))
        console.print("[green]✓ patch applied (direct)[/]")
        return True

    # 2️⃣ smart insert
    console.print("[yellow]Direct apply failed → smart insert hunks…[/]")
    smart, idx, inserted = original[:], 0, False
    for h in target:
        ctx_line = next((l.value for l in h if l.is_context), None)
        if ctx_line and ctx_line in smart:
            anchor = smart.index(ctx_line)
            smart[anchor:anchor] = [l.value for l in h if l.is_added]
            inserted = True
        else:
            inserted = False
            break
    if inserted:
        spec_path.write_text("".join(smart))
        console.print("[green]✓ patch applied (smart insert)[/]")
        return True

    # 3️⃣ append fallback
    console.print("[red]Smart insert failed → appending diff at EOF.[/]")
    with spec_path.open("a") as f:
        f.write("\n<!-- OUT-OF-ORDER PATCH {} -->\n".format(datetime.utcnow().isoformat()))
        f.write(diff_text)
    return True

# ───────────────── Reorder helper ────────────────────────────────────────

def reorder_headings(md_text: str) -> str:
    pattern = re.compile(r"(^# .+?$)", re.M | re.S)
    parts = pattern.split(md_text)
    intro = parts[0]
    titled = list(zip(parts[1::2], parts[2::2]))  # (H1, body)
    titled.sort(key=lambda t: t[0].lower())
    return intro + "".join(h + b for h, b in titled)

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

# ───────────────── Main ──────────────────────────────────────────────────

def main():
    if "--reorder" in sys.argv:
        SPEC_PATH.write_text(reorder_headings(SPEC_PATH.read_text()))
        console.print("[green]Headings reordered alphabetically.[/]")
        return
    interactive()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted.[/]")
