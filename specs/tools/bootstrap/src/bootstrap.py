# --- Self-rebuild and self-improve helpers ---
def rebuild_from_spec():
    """Regenerate this script from its own specification and docstrings."""
    # Read the spec (top-level docstring)
    spec_text = SPEC_PATH.read_text()
    # Compose prompt for LLM
    prompt = [
        {"role": "system", "content": SYS_REBUILD},
        {"role": "user", "content": spec_text},
    ]
    new_code = ask_llm(prompt)
    # Write new code to a new git branch, not in-place
    import subprocess
    import shutil
    from datetime import datetime
    script_path = pathlib.Path(__file__)
    repo_root = script_path.parent.parent.parent.parent  # /codecraft
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"selfedit/{ts}"
    # Write the new code to the same file path (in the new branch only)
    script_path.write_text(new_code)
    # Attempt git operations in a new branch; on failure, warn and continue
    try:
        # Create new branch from current HEAD
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_root, check=True)
        subprocess.run(["git", "add", str(script_path.relative_to(repo_root))], cwd=repo_root, check=True)
        subprocess.run(["git", "commit", "-m", f"Self-edit: regenerate bootstrap.py from spec at {ts}"], cwd=repo_root, check=True)
        # Push the branch to origin
        subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=repo_root, check=True)
        # Create a pull request using GitHub CLI (gh)
        pr_title = f"Self-edit: bootstrap.py regenerated from spec at {ts}"
        pr_body = "Automated self-edit by CodeCraft bootstrap tool. Please review before merging."
        subprocess.run([
            "gh", "pr", "create",
            "--title", pr_title,
            "--body", pr_body,
            "--base", "main",
            "--head", branch_name
        ], cwd=repo_root, check=True)
        console.print(f"[green]✓ bootstrap.py self-edit committed and PR opened from branch {branch_name}[/]")
    except Exception as e:
        console.print(f"[yellow]Warning: self-edit git operations failed: {e}[/]")

def improve_tool(turns: int = 4):
    """Run self-improvement cycles on the bootstrap specification, then rebuild and test after each turn."""
    spec = SPEC_PATH.read_text()
    for step in range(1, turns + 1):
        spec = auto_turn(spec, step)
        SPEC_PATH.write_text(spec)
        console.print(f"[blue]✓ Self-improvement turn {step} complete[/]")
        rebuild_from_spec()
        # Run tests after each turn
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, '-m', 'pytest', '--maxfail=1', '--disable-warnings', '-v'
            ], cwd=pathlib.Path(__file__).parent.parent, capture_output=True, text=True)
            if result.returncode == 0:
                console.print("[green]✓ All tests passed after self-improvement turn[/]")
            else:
                console.print(f"[red]❌ Tests failed after self-improvement turn {step}[/]\n{result.stdout}\n{result.stderr}")
        except Exception as e:
            console.print(f"[red]❌ Error running tests after self-improvement turn {step}: {e}")
#!/usr/bin/env python
## (already present at top, remove duplicate)
"""
bootstrap_spec_dialog.py (v0.7)
--------------------------------
A Spec-First Two-Persona Dialog Tool for Refining Markdown Specifications

This script accelerates the creation and refinement of software specs by orchestrating a structured
conversation between two roles:
  • PM-Interviewer: probes the current spec with focused questions.
  • Architect-Responder: provides concise, well-defined technical guidance.

Features:
  - Manual Mode (default): one-turn PM question followed by your architect answer and automated patch.
  - Auto Mode (`--auto`): runs configurable cycles of PM⇄Architect exchanges and applies diffs.
  - Prompt Management: all system prompts live in `src/prompts/` via prompty.ai for easy customization.
  - Patch Pipeline: attempts direct diff apply, context-smart insert, and a pending-updates fallback.
  - Azure OpenAI Integration: uses `AzureOpenAI` client with DefaultAzureCredential for token-based auth.
  - Local-First Workflow: edits local Markdown spec files, supports safe rollbacks and manual overrides.
  - Self-Rebuild (`--rebuild`): regenerate bootstrap.py from its own specification and docstrings.
  - Self-Improve (`--improve`): run iterative self-improvement cycles refining specification and code.

Backlog Goals:
  1. Evolve specs through dialogue-driven refinement.
  2. Ensure reliable patching with robust failure recovery.
  3. Keep prompts and logic modular for future extensions.
  4. Provide transparent audit trails of spec changes.

Environment Variables:
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_DEPLOYMENT
  - AZURE_OPENAI_API_VERSION

CLI Flags:
  - --auto                 Run automatic PM⇄Architect cycles
  - --turns <n> (default 4) Number of auto mode turns
  - --rebuild              Regenerate this tool's code from its spec and docstrings
  - --improve              Run self-improvement cycles on the bootstrap specification
"""
__all__ = [
    "rebuild_from_spec",
    "improve_tool",
    "apply_patch_pipeline",
    "auto_turn",
    "manual_loop",
    "ask_llm",
    "apply_diff_direct",
    "apply_semantic_patch",
    "_apply_diff",
    "reorder_headings",
    "azure_cli_login",
    "main",
]
"""
bootstrap_spec_dialog.py (v0.7)
--------------------------------
A Spec-First Two-Persona Dialog Tool for Refining Markdown Specifications

This script accelerates the creation and refinement of software specs by orchestrating a structured
conversation between two roles:
  • PM-Interviewer: probes the current spec with focused questions.
  • Architect-Responder: provides concise, well-defined technical guidance.

Features:
  - Manual Mode (default): one-turn PM question followed by your architect answer and automated patch.
  - Auto Mode (`--auto`): runs configurable cycles of PM⇄Architect exchanges and applies diffs.
  - Prompt Management: all system prompts live in `src/prompts/` via prompty.ai for easy customization.
  - Patch Pipeline: attempts direct diff apply, context-smart insert, and a pending-updates fallback.
  - Azure OpenAI Integration: uses `AzureOpenAI` client with DefaultAzureCredential for token-based auth.
  - Local-First Workflow: edits local Markdown spec files, supports safe rollbacks and manual overrides.
  - Self-Rebuild (`--rebuild`): regenerate bootstrap.py from its own specification and docstrings.
  - Self-Improve (`--improve`): run iterative self-improvement cycles refining specification and code.

Backlog Goals:
  1. Evolve specs through dialogue-driven refinement.
  2. Ensure reliable patching with robust failure recovery.
  3. Keep prompts and logic modular for future extensions.
  4. Provide transparent audit trails of spec changes.

Environment Variables:
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_DEPLOYMENT
  - AZURE_OPENAI_API_VERSION

CLI Flags:
  - --auto                 Run automatic PM⇄Architect cycles
  - --turns <n> (default 4) Number of auto mode turns
  - --rebuild              Regenerate this tool's code from its spec and docstrings
  - --improve              Run self-improvement cycles on the bootstrap specification
"""

import os, sys, pathlib, re, subprocess
from datetime import datetime
from typing import List
import json
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.panel import Panel
from unidiff import PatchSet, PatchedFile
from unidiff.errors import UnidiffParseError
# Optional AST diff integration (requires `unified_diff_to_ast`)
try:
    from unified_diff_to_ast import unified_diff_to_ast
except ImportError:
    unified_diff_to_ast = None
try:
    # Full-blown AST diff integration (optional dependency)
    from unified_diff_to_ast import unified_diff_to_ast
except ImportError:
    unified_diff_to_ast = None
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
# Import patching utilities as a standalone module
from patching.patcher import (
    _apply_diff,
    apply_diff_direct,
    apply_semantic_patch,
    reorder_headings,
    apply_patch_pipeline,
)
import argparse
# --- Logging utility ---
# --- Logging utility ---
from log_utils import AuditLogger
  
# --- Patching overrides: delegate diff/patch functions to standalone module ---
import patching.patcher as _p
_apply_diff = _p._apply_diff
apply_diff_direct = _p.apply_diff_direct
apply_semantic_patch = _p.apply_semantic_patch
reorder_headings = _p.reorder_headings
apply_patch_pipeline = _p.apply_patch_pipeline

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

# AUTO_TURNS env var no longer used; default turns via CLI parameter

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
SYS_PM_ASK      = load_prompt('pm_ask')        # senior PM clarifying question prompt
SYS_ARCH_ANSWER = load_prompt('arch_answer')   # architect answer prompt
SYS_PATCH       = load_prompt('sys_patch')     # editor patch creation prompt
SYS_PENDING     = load_prompt('pending_patch') # apply pending updates prompt
SYS_REBUILD     = load_prompt('rebuild')       # regenerate tool code from spec prompt

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
    # Audit log
    if hasattr(ask_llm, "logger") and ask_llm.logger:
        ask_llm.logger.log({
            "event": "llm_call",
            "prompt": messages,
            "response": response
        })
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
    
def apply_semantic_patch(spec_path: pathlib.Path, diff_text: str) -> bool:
    """Attempt semantic Markdown patch by inserting additions into logical sections."""
    console.print("[yellow]Attempting semantic section-based patch…")
    # Strip fences and parse patch hunks
    lines = diff_text.splitlines(keepends=True)
    lines = [l for l in lines if not l.strip().startswith('```')]
    clean_diff = ''.join(lines)
    try:
        patchset = PatchSet(clean_diff.splitlines(keepends=True))
        if not patchset:
            return False
        target = patchset[0]
        original = spec_path.read_text().splitlines(keepends=True)
        updated = original[:]
        for h in target:
            # collect added lines
            additions = [ln.value for ln in h if ln.is_added]
            if not additions:
                continue
            # find context line index in original
            context = h.source_start - 1
            if context < 0 or context >= len(original):
                insert_at = len(updated)
            else:
                # determine section heading above context
                insert_at = len(updated)
                heading_idx = None
                # search in updated for context value
                ctx_val = original[context]
                try:
                    idx = updated.index(ctx_val)
                except ValueError:
                    idx = None
                # find nearest heading before idx
                if idx is not None:
                    for i in range(idx, -1, -1):
                        if re.match(r"^#{1,6} ", updated[i]):
                            heading_idx = i
                            level = updated[i].count('#', 0, updated[i].find(' '))
                            break
                if heading_idx is not None:
                    # default insert immediately after heading
                    insert_at = heading_idx + 1
                    # shift if next same-or-higher heading appears
                    for j in range(heading_idx+1, len(updated)):
                        m = re.match(r"^(#{1,6}) ", updated[j])
                        if m and len(m.group(1)) <= level:
                            insert_at = j
                            break
                else:
                    insert_at = len(updated)
            # insert additions at insert_at
            for offset, line in enumerate(additions):
                updated.insert(insert_at + offset, line)
        spec_path.write_text(''.join(updated))
        return True
    except Exception as e:
        console.print(f"[red]Semantic patch error: {e}")
        return False
    
def apply_diff_direct(spec_path: pathlib.Path, diff_text: str) -> bool:
    """Attempt direct and smart insert without fallback; return True if applied."""
    try:
        # Strip Markdown fences
        lines = diff_text.splitlines(keepends=True)
        lines = [l for l in lines if not l.strip().startswith('```')]
        clean_diff = ''.join(lines)
        original = spec_path.read_text().splitlines(keepends=True)
        patchset = PatchSet(clean_diff.splitlines(keepends=True))
        if not patchset:
            return False
        target = patchset[0]
        # direct
        patched = _apply_diff(original, target)
        if patched:
            spec_path.write_text(''.join(patched))
            return True
        # smart insert
        smart = original[:]
        for h in target:
            ctx = next((l.value for l in h if l.is_context), None)
            if ctx and ctx in smart:
                added = [l.value for l in h if l.is_added]
                pos = smart.index(ctx)
                for offset, line in enumerate(added):
                    smart.insert(pos + offset, line)
            else:
                return False
        spec_path.write_text(''.join(smart))
        return True
    except Exception:
        # parse or apply error
        return False


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
    Logs all patch attempts and results.
    """
    patch_result = {"event": "patch_attempt", "diff": diff_text}
    try:
        # Strip Markdown code fences to extract raw diff
        lines = diff_text.splitlines(keepends=True)
        lines = [l for l in lines if not l.strip().startswith("```")]
        clean_diff = "".join(lines)
        original = spec_path.read_text().splitlines(keepends=True)
        # Parse patchset
        patchset = PatchSet(clean_diff.splitlines(keepends=True))
        if not patchset:
            console.print("[red]❌ Empty diff from LLM");
            patch_result["result"] = "empty_diff"; raise RuntimeError("empty diff")
        target = patchset[0]
        # Direct apply
        patched = _apply_diff(original, target)
        if patched:
            spec_path.write_text("".join(patched))
            console.print("[green]✓ patch applied (direct)")
            patch_result["result"] = "direct"
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
            patch_result["result"] = "smart"
            return
        # Full AST-driven patch fallback (P0.2)
        if unified_diff_to_ast:
            console.print("[yellow]Attempting AST-driven patch…")
            try:
                # Parse unified diff to AST patch and apply
                patch_ast = unified_diff_to_ast(diff_text)
                new_md = patch_ast.apply(spec_path.read_text())
                spec_path.write_text(new_md)
                console.print("[green]✓ patch applied (ast)")
                patch_result["result"] = "ast"
                return
            except Exception as e:
                console.print(f"[red]AST patch error: {e}")
        # Semantic AST-based patch fallback (P0)
        if apply_semantic_patch(spec_path, diff_text):
            console.print("[green]✓ patch applied (semantic)")
            patch_result["result"] = "semantic"
            return
        # Append & reorder fallback
        raise RuntimeError("smart insert context missing")
    except Exception as e:
        console.print(f"[red]❌ Patch pipeline failed: {e}\n→ fallback: pending updates")
        patch_result["result"] = f"failed: {e}"
        # Append Pending Updates section with table
        orig = spec_path.read_text()
        pending = (
            "\n## Pending Updates\n\n"
            "| Section to update | Proposed changes |\n"
            "| --- | --- |\n"
            f"|  | ```diff\n{diff_text.strip()}\n``` |\n"
        )
        spec_path.write_text(orig + pending)
        console.print("[yellow]⚠ Pending Updates section appended")
        # Generate patch from pending updates
        full_spec = spec_path.read_text()
        pending_diff = ask_llm([
            {"role": "system", "content": SYS_PENDING},
            {"role": "user",   "content": full_spec},
        ])
        console.print(Panel(pending_diff, title="Pending Patch", style="yellow"))
        # Attempt direct apply of pending patch
        try:
            if apply_diff_direct(spec_path, pending_diff):
                console.print("[green]✓ pending updates applied")
                patch_result["result"] = "pending_applied"
            else:
                console.print("[red]❌ pending updates failed")
                patch_result["result"] = "pending_failed"
        except Exception as e:
            console.print(f"[red]❌ pending updates error: {e}")
            patch_result["result"] = f"pending_error: {e}"
        return
    finally:
        if hasattr(apply_patch_pipeline, "logger") and apply_patch_pipeline.logger:
            apply_patch_pipeline.logger.log(patch_result)


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
        "--rebuild", action="store_true",
        help="Regenerate bootstrap.py from its spec and docstrings"
    )
    parser.add_argument(
        "--improve", action="store_true",
        help="Run self-improvement loop against bootstrap spec before rebuilding"
    )
    parser.add_argument(
        "--turns", "-t", type=int, default=4,
        help="Number of auto mode turns to run"
    )
    parser.add_argument(
        "--spec", "-s", type=str, default=None,
        help="Path to the Markdown spec file to operate on"
    )
    parser.add_argument(
        "--emit-spec", action="store_true",
        help="Extract the module docstring spec to its own markdown file and exit"
    )
    args = parser.parse_args()
    # Handle emit-spec: dump top-level docstring spec
    if args.emit_spec:
        import inspect
        # Get module docstring
        doc = inspect.getdoc(sys.modules[__name__]) or ""
        # Write to specs/bootstrap_tool_spec.md
        out_path = pathlib.Path(__file__).parent / "specs" / "bootstrap_tool_spec.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(doc)
        console.print(f"[green]✓ Spec extracted to {out_path}")
        return
    # Allow overriding SPEC_PATH via CLI
    if args.spec:
        global SPEC_PATH, TMP_SPEC_PATH
        SPEC_PATH = pathlib.Path(args.spec)
        TMP_SPEC_PATH = SPEC_PATH.with_suffix(SPEC_PATH.suffix + ".tmp")
        # ensure directory exists
        SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Azure CLI login should happen at runtime
    azure_cli_login()
    # Set up audit logger and inject into LLM/patch pipeline
    logger = AuditLogger()
    ask_llm.logger = logger
    apply_patch_pipeline.logger = logger
    # Self-improve or rebuild workflow
    if args.rebuild:
        rebuild_from_spec()
        return
    if args.improve:
        improve_tool(args.turns)
        return
    # Normal operation
    if args.auto:
        auto_loop(args.turns)
    else:
        manual_loop()

    logger.close()

if __name__ == "__main__":
    main()
