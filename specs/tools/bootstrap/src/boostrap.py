#!/usr/bin/env python
"""
bootstrap_spec_dialog.py  (v0.7)
--------------------------------
Interactive (manual) **and** automatic two‑persona refinement of a Markdown spec.

Personae
========
• **PM‑Interviewer** – asks one clarifying question per turn.
• **Architect‑Responder** – expert software architect; answers with clear, concise guidance.

Modes
=====
1. **Manual** (default) – PM asks a question, *you* answer.
2. **Auto** (`--auto`) – PM and Architect converse for `AUTO_TURNS` cycles (from `.env`).
   After those turns the script pauses for user input:
      `[c]ontinue  [e]dit spec manually  [d]one`

Key Features
============
• Azure OpenAI bearer‑token auth (DefaultAzureCredential).
• Patch apply pipeline: direct → smart‑insert → append & reorder headings.
• Optional heading re‑order utility (`--reorder`).
• Config loaded from `$REPO/.codecraft/.env` or fallback `.env`.

Guardrails
==========
• No plaintext OpenAI keys committed.
• On patch failure never overwrite spec blindly.

Env Vars
========
AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, AUTO_TURNS (default 4)
"""
from __future__ import annotations
import os, sys, pathlib, re, subprocess
from datetime import datetime
from typing import List
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.panel import Panel
from unidiff import PatchSet, PatchedFile
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import argparse

console = Console()

# ── .env loading ─────────────────────────────────────────────────────────
ROOT = pathlib.Path.cwd()
CODECRAFT_ENV = ROOT / ".codecraft" / ".env"
if CODECRAFT_ENV.exists():
    load_dotenv(dotenv_path=CODECRAFT_ENV, override=False)
else:
    fe = find_dotenv(usecwd=True)
    if fe:
        load_dotenv(fe, override=False)

AUTO_TURNS = int(os.getenv("AUTO_TURNS", "4"))

"""
Azure CLI login logic moved to `azure_cli_login` function to avoid execution on import.
"""

def azure_cli_login():
    """Perform Azure CLI login and set subscription based on env vars."""
    tenant = os.getenv("AZURE_TENANT_ID")
    subscription = os.getenv("AZURE_SUBSCRIPTION_ID")
    if tenant:
        console.print(f"[blue]Logging in to Azure tenant {tenant}[/]")
        subprocess.run(["az", "login", "--tenant", tenant], check=True)
    if subscription:
        console.print(f"[blue]Setting default subscription to {subscription}[/]")
        subprocess.run(["az", "account", "set", "--subscription", subscription], check=True)

# ── Azure OpenAI client ──────────────────────────────────────────────────
ENDPOINT   = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
API_VERS   = os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")

client = AzureOpenAI(
    azure_endpoint=ENDPOINT,
    api_version=API_VERS,
    azure_ad_token_provider=get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    ),
)

# ── Paths ────────────────────────────────────────────────────────────────
SPEC_PATH     = ROOT / "specs" / "00_Overview.md"
TMP_SPEC_PATH = SPEC_PATH.with_suffix(SPEC_PATH.suffix + ".tmp")   # add .tmp suffix
SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
if not SPEC_PATH.exists():
    SPEC_PATH.write_text("# Rough Sketch\n\n_TODO: describe your idea here._\n")

# ── System prompts ───────────────────────────────────────────────────────
SYS_PM_ASK = (
    "You are a senior PM AI interviewing an expert architect. From the current "
    "Markdown spec, ask **one** clarifying question that will move the spec closer "
    "to a shippable overview."
)

SYS_ARCH_ANSWER = (
    "You are an expert software architect. Answer the PM's question with clear, concise "
    "guidance—well‑specified, elegant, compact. If you feel unsure, prefix your answer "
    "with 'SEARCH:' followed by a query you would run. Keep creativity reasonable."
)

SYS_PATCH = (
    "You are an expert editor. Given the architect's answer and the current spec, "
    "output a unified git diff that updates the Markdown spec accordingly."
)

def ask_llm(messages: List[dict]) -> str:
    return client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        max_completion_tokens=2048,
    ).choices[0].message.content.strip()

# ── Diff helpers ─────────────────────────────────────────────────────────

def _apply_diff(original: List[str], patch: PatchedFile) -> List[str] | None:
    idx, out = 0, []
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
    parts = re.split(r"(?m)^# (.+)$", md_text)
    intro = parts[0]
    titled = list(zip(parts[1::2], parts[2::2]))
    titled.sort(key=lambda t: t[0].lower())
    return intro + "".join(f"# {h}{b}" for h, b in titled)


def apply_patch_pipeline(spec_path: pathlib.Path, diff_text: str) -> None:
    original = spec_path.read_text().splitlines(keepends=True)
    patchset = PatchSet(diff_text.splitlines(keepends=True))
    if not patchset:
        console.print("[red]❌ Empty diff from LLM"); return
    target = patchset[0]

    # direct
    patched = _apply_diff(original, target)
    if patched:
        spec_path.write_text("".join(patched))
        console.print("[green]✓ patch applied (direct)")
        return

    # smart insert
    console.print("[yellow]Direct failed → smart insert…")
    smart = original[:]
    for h in target:
        ctx = next((l.value for l in h if l.is_context), None)
        if ctx and ctx in smart:
            smart.insert(smart.index(ctx), *(l.value for l in h if l.is_added))
        else:
            break
    else:
        spec_path.write_text("".join(smart))
        console.print("[green]✓ patch applied (smart)")
        return

    # append fallback + reorder
    console.print("[red]Smart insert failed → append & reorder headings")
    marker = f"\n<!-- OUT-OF-ORDER PATCH {datetime.utcnow().isoformat()} -->\n"
    spec_path.write_text(spec_path.read_text() + marker + diff_text)
    spec_path.write_text(reorder_headings(spec_path.read_text()))
    console.print("[green]✓ appended & reordered")

# ── Auto dialog helpers ──────────────────────────────────────────────────

def auto_turn(spec_text: str) -> str:
    """Run one interviewer→architect→patch cycle and return new spec text."""
    question = ask_llm([
        {"role": "system", "content": SYS_PM_ASK},
        {"role": "user", "content": spec_text},
    ])
    answer = ask_llm([
        {"role": "system", "content": SYS_ARCH_ANSWER},
        {"role": "user", "content": question},
    ])
    console.print(Panel(question, title="PM Question", style="cyan"))
    console.print(Panel(answer, title="Architect Answer", style="green"))
    diff = ask_llm([
        {"role": "system", "content": SYS_PATCH},
        {"role": "user", "content": f"SPEC:\n{spec_text}\nANSWER:\n{answer}"},
    ])
    console.print(Panel(diff, title="Patch", style="magenta"))
    apply_patch_pipeline(SPEC_PATH, diff)
    return SPEC_PATH.read_text()

# ───────────────── Interactive loops ─────────────────────────────────────

def manual_loop():
    # initialize temp file from real spec if not present
    if not TMP_SPEC_PATH.exists():
        TMP_SPEC_PATH.write_text(SPEC_PATH.read_text())
    spec = TMP_SPEC_PATH.read_text()
    while True:
        q = ask_llm([
            {"role": "system", "content": SYS_PM_ASK},
            {"role": "user",   "content": spec},
        ])
        console.print(Panel(q, title="Clarifying Question", style="cyan"))
        ans = console.input("[bold green]Your answer (/save to commit, /done to exit): [/] ")
        cmd = ans.strip().lower()
        if cmd == "/save":
            TMP_SPEC_PATH.replace(SPEC_PATH)
            console.print(f"[green]✓ Saved changes to {SPEC_PATH}")
            # re-init temp from saved spec
            TMP_SPEC_PATH.write_text(SPEC_PATH.read_text())
            spec = TMP_SPEC_PATH.read_text()
            continue
        if cmd == "/done":
            TMP_SPEC_PATH.unlink(missing_ok=True)
            break
        # for any other input, treat as architect answer
        diff = ask_llm([
            {"role": "system", "content": SYS_PATCH},
            {"role": "user",   "content": f"SPEC:\n{spec}\nANSWER:\n{ans}"},
        ])
        console.print(Panel(diff, title="Proposed Patch", style="magenta"))
        apply_patch_pipeline(TMP_SPEC_PATH, diff)
        spec = TMP_SPEC_PATH.read_text()


def auto_loop():
    spec = SPEC_PATH.read_text()
    for _ in range(AUTO_TURNS):
        spec = auto_turn(spec)
    while True:
        cmd = console.input(
            "[bold cyan]Auto mode done. Edit spec manually, or choose an action:  "
            "[/]\n  [c]ontinue  [e]dit spec manually  [d]one\n> "
        ).strip().lower()
        if cmd == "c":
            spec = auto_turn(spec)
        elif cmd == "e":
            manual_loop()
            break
        elif cmd == "d":
            break
        else:
            console.print("[red]❌ Invalid command.")

# add module entry point
def main():
    parser = argparse.ArgumentParser(
        description="Interactive two-persona spec bootstrap"
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="Run in auto mode (automatic PM⇄Architect cycles)"
    )
    args = parser.parse_args()
    # Azure CLI login should happen at runtime, not import
    azure_cli_login()
    if args.auto:
        auto_loop()
    else:
        manual_loop()

if __name__ == "__main__":
    main()
