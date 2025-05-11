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
import json
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.panel import Panel
from unidiff import PatchSet, PatchedFile
from unidiff.errors import UnidiffParseError
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import argparse

# Initialize console
console = Console()
# ── Prompt loading via prompty.ai framework ─────────────────────────────
# Separate prompt templates into files under 'prompts/' directory
SCRIPT_DIR = pathlib.Path(__file__).parent
PROMPT_DIR = SCRIPT_DIR / 'prompts'
def load_prompt(name: str) -> str:
    """Load prompt template from prompts/<name>.txt"""
    path = PROMPT_DIR / f"{name}.txt"
    return path.read_text().strip()

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
    # If already logged in, skip further Azure CLI login
    try:
        subprocess.run(["az", "account", "show"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        console.print("[blue]Azure CLI already logged in; skipping login[/]")
        return
    except subprocess.CalledProcessError:
        pass
    tenant = os.getenv("AZURE_TENANT_ID")
    subscription = os.getenv("AZURE_SUBSCRIPTION_ID")
    # Combine tenant and subscription into one login call if both provided
    if tenant or subscription:
        cmd = ["az", "login"]
        msg_parts = []
        if tenant:
            cmd.extend(["--tenant", tenant])
            msg_parts.append(f"tenant {tenant}")
        if subscription:
            # Use --subscription flag on login to set default subscription
            cmd.extend(["--subscription", subscription])
            msg_parts.append(f"subscription {subscription}")
        console.print(f"[blue]Logging in to Azure {' and '.join(msg_parts)}[/]")
        subprocess.run(cmd, check=True)
    else:
        console.print("[yellow]No AZURE_TENANT_ID or AZURE_SUBSCRIPTION_ID set; skipping Azure CLI login[/]")

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

## ── System prompts loaded from files via prompty.ai ──────────────────────
SYS_PM_ASK      = load_prompt('pm_ask')      # senior PM clarifying question prompt
SYS_ARCH_ANSWER = load_prompt('arch_answer') # architect answer prompt
SYS_PATCH      = load_prompt('sys_patch')    # editor patch creation prompt

def ask_llm(messages: List[dict]) -> str:
    # Log the prompt payload before sending to LLM
    prompt_str = json.dumps(messages, indent=2)
    console.print(Panel(prompt_str, title="Prompt Payload", style="grey50 italic", border_style="grey70"))
    console.rule("—")  # separator
    # Invoke LLM
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        max_completion_tokens=16192,
    ).choices[0].message.content.strip()
    # Log the LLM response after call
    console.print(Panel(response, title="LLM Response", style="bright_blue italic", border_style="blue"))
    return response

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
    """
    Apply a unified diff to the spec file. On any parsing or patching error,
    fall back to appending the raw diff and reordering headings.
    """
    try:
        # Strip Markdown code fences to extract raw diff
        lines = diff_text.splitlines(keepends=True)
        lines = [l for l in lines if not l.strip().startswith("```")]
        clean_diff = "".join(lines)
        original = spec_path.read_text().splitlines(keepends=True)
        # Parse patchset
        patchset = PatchSet(clean_diff.splitlines(keepends=True))
        if not patchset:
            console.print("[red]❌ Empty diff from LLM"); return
        target = patchset[0]
        # Direct apply
        patched = _apply_diff(original, target)
        if patched:
            spec_path.write_text("".join(patched))
            console.print("[green]✓ patch applied (direct)")
            return
        # Smart insert fallback
        console.print("[yellow]Direct failed → smart insert…")
        smart = original[:]
        for h in target:
            ctx = next((l.value for l in h if l.is_context), None)
            if ctx and ctx in smart:
                added = [l.value for l in h if l.is_added]
                pos = smart.index(ctx)
                for offset, line in enumerate(added):
                    smart.insert(pos + offset, line)
            else:
                break
        else:
            spec_path.write_text("".join(smart))
            console.print("[green]✓ patch applied (smart)")
            return
        # Append & reorder fallback
        raise RuntimeError("smart insert context missing")
    except Exception as e:
        console.print(f"[red]❌ Patch pipeline failed: {e}\n→ fallback: append & reorder headings")
        marker = f"\n<!-- OUT-OF-ORDER PATCH {datetime.utcnow().isoformat()} -->\n"
        spec_path.write_text(spec_path.read_text() + marker + diff_text)
        spec_path.write_text(reorder_headings(spec_path.read_text()))
        console.print("[green]✓ appended & reordered")
        return  # exit after fallback


# ── Auto dialog helpers ──────────────────────────────────────────────────

def auto_turn(spec_text: str, step: int) -> str:
    """Run one interviewer→architect→patch cycle and return new spec text."""
    question = ask_llm([
        {"role": "system", "content": SYS_PM_ASK},
        {"role": "user", "content": spec_text},
    ])
    answer = ask_llm([
        {"role": "system", "content": SYS_ARCH_ANSWER},
        {"role": "user", "content": question},
    ])
    console.print(Panel(question, title="PM Question", style="cyan", subtitle=f"Step {step}", subtitle_align="center"))
    console.print(Panel(answer, title="Architect Answer", style="green", subtitle=f"Step {step}", subtitle_align="center"))
    diff = ask_llm([
        {"role": "system", "content": SYS_PATCH},
        {"role": "user", "content": f"SPEC:\n{spec_text}\nANSWER:\n{answer}"},
    ])
    console.print(Panel(diff, title="Patch", style="magenta", subtitle=f"Step {step}", subtitle_align="center"))
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


def auto_loop(turns: int):
    """Run automatic PM⇄Architect cycles for the given number of turns with step tracking."""
    spec = SPEC_PATH.read_text()
    step = 1
    # initial auto turns
    for _ in range(turns):
        spec = auto_turn(spec, step)
        step += 1
    # post-turn interactive continue
    while True:
        cmd = console.input(
            "[bold cyan]Auto mode done. Edit spec manually, or choose an action:  "
            "[/]\n  [c]ontinue  [e]dit spec manually  [d]one\n> "
        ).strip().lower()
        if cmd == "c":
            spec = auto_turn(spec, step)
            step += 1
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
    parser.add_argument(
        "--turns", "-t", type=int, default=None,
        help="Number of auto mode turns to run (overrides AUTO_TURNS env var)"
    )
    parser.add_argument(
        "--spec", "-s", type=str, default=None,
        help="Path to the Markdown spec file to operate on"
    )
    args = parser.parse_args()
    # Allow overriding SPEC_PATH via CLI
    if args.spec:
        global SPEC_PATH, TMP_SPEC_PATH
        SPEC_PATH = pathlib.Path(args.spec)
        TMP_SPEC_PATH = SPEC_PATH.with_suffix(SPEC_PATH.suffix + ".tmp")
        # ensure directory exists
        SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Azure CLI login should happen at runtime
    azure_cli_login()
    if args.auto:
        # Determine number of turns: CLI overrides env var
        turns = args.turns if args.turns is not None else AUTO_TURNS
        auto_loop(turns)
    else:
        manual_loop()

if __name__ == "__main__":
    main()
