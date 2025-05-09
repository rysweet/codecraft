#!/usr/bin/env python
"""
bootstrap_spec_dialog.py
--------------------------------
Walks through a spec-refinement dialog one question at a time.

❏ Requires
    pip install openai azure-identity python-dotenv rich unidiff

❏ Environment
    AZURE_OPENAI_ENDPOINT   # e.g. https://my-oai.openai.azure.com
    (deployment defaults to env AZURE_OPENAI_DEPLOYMENT or 'gpt-4o')
"""

import os, sys, pathlib, subprocess, tempfile, shutil
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from unidiff import PatchSet
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
ROOT       = pathlib.Path.cwd()
SPEC_PATH  = ROOT / "specs" / "00_overview.md"
SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
if not SPEC_PATH.exists():
    SPEC_PATH.write_text("# Rough Sketch\n\n_TODO: describe your idea here._\n")

# ── Prompts ────────────────────────────────────────────────────────────────
SYS_ASK = (
    "You are a senior program-manager AI. From the current Markdown spec, "
    "output exactly *one* clarifying question. No answers, no preamble."
)
SYS_PATCH = (
    "You are an expert technical editor. Given the user's answer, output a "
    "unified **diff** patch (git format) that updates the Markdown spec. "
    "Do not wrap the diff in markdown fences."
)

def ask_llm(messages: list[dict], **params) -> str:
    return client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        max_completion_tokens=2048,
        **params,
    ).choices[0].message.content.strip()

# ── Diff application helper ────────────────────────────────────────────────
def apply_patch(spec_path: pathlib.Path, diff_text: str) -> bool:
    """
    Apply a unified diff to spec_path. Returns True on success.
    On failure, writes .rej file and returns False.
    """
    patch = PatchSet(diff_text.splitlines(keepends=True))
    # unidiff expects exact paths; ensure the patch references the spec filename
    target_file = patch[0]
    if not target_file.path.endswith(spec_path.name):
        console.print(f"[yellow]Patch references {target_file.path}, expected {spec_path.name}. Trying anyway…[/]")

    original = spec_path.read_text().splitlines(keepends=True)
    tok      = target_file
    newlines = []
    idx      = 0
    for hunk in tok:
        # copy unchanged lines until hunk start
        while idx < hunk.source_start - 1:
            newlines.append(original[idx]); idx += 1
        for line in hunk:
            if line.is_context or line.is_added:
                newlines.append(line.value)
            if not line.is_added:
                idx += 1
    # copy the tail
    newlines.extend(original[idx:])

    backup = spec_path.with_suffix(".bak")
    shutil.copy2(spec_path, backup)
    spec_path.write_text("".join(newlines))
    console.print("[green]✓ patch applied[/]")
    return True

# ── Main loop ──────────────────────────────────────────────────────────────
def main():
    spec_text = SPEC_PATH.read_text()
    while True:
        question = ask_llm(
            [{"role": "system", "content": SYS_ASK},
             {"role": "user", "content": spec_text}]
        )
        console.print(Panel(question, title="Clarifying Question", style="cyan"))
        answer = console.input("[bold green]Your answer (type /done to finish): [/]")
        if answer.strip().lower() == "/done":
            console.print("[yellow]Finished dialog. Exiting…[/]")
            break

        diff = ask_llm(
            [{"role": "system", "content": SYS_PATCH},
             {"role": "user", "content": f"SPEC:\n{spec_text}\n\nANSWER:\n{answer}"}]
        )
        console.print(Panel(diff, title="Proposed Patch", style="magenta"))

        try:
            apply_patch(SPEC_PATH, diff)
            spec_text = SPEC_PATH.read_text()
        except Exception as e:
            rej = SPEC_PATH.with_suffix(".rej")
            rej.write_text(diff)
            console.print(f"[red]Patch failed, saved to {rej}[/] :: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted.[/]")