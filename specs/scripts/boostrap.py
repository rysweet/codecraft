#!/usr/bin/env python
"""
bootstrap_spec_dialog.py
--------------------------------
Interactive helper that iteratively refines a Markdown spec,
one question/answer pair at a time.

Prereqs:
  pip install openai azure-identity python-dotenv rich
  # .env-template -> copy to .env and fill AZURE_OPENAI_ENDPOINT
"""

import os
import pathlib
import sys
from datetime import datetime
from dotenv import load_dotenv
from rich import print, box
from rich.console import Console
from rich.panel import Panel
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

console = Console()
load_dotenv()

### ───────────────────────── Azure OpenAI client ────────────────────────── ###
ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]         # e.g. https://your-oai.openai.azure.com
DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
API_VERSION = "2025-03-01-preview"

client = AzureOpenAI(
    azure_endpoint=ENDPOINT,
    api_version=API_VERSION,
    azure_ad_token_provider=get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    ),
)

### ───────────────────────── paths & helpers ─────────────────────────────── ###
ROOT = pathlib.Path.cwd()
STATE_DIR = ROOT / ".codecraft"
STATE_DIR.mkdir(exist_ok=True)
SPEC_PATH = ROOT / "specs" / "00_overview.md"
SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
if not SPEC_PATH.exists():
    SPEC_PATH.write_text("# Rough Sketch\n\n_TODO: describe your idea here._\n")

def ask_llm(messages: list[dict], **params):
    return client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        max_completion_tokens=2048,
        **params,
    ).choices[0].message.content.strip()

### ───────────────────────── system prompts ──────────────────────────────── ###
SYS_ASK = (
    "You are a senior program-manager AI. Given the current Markdown spec, "
    "output **one** clarifying question that will move the spec toward a shippable overview. "
    "Do NOT propose answers. Do NOT output anything except the question."
)

SYS_PATCH = (
    "You are an expert technical editor. Given the user's answer, produce a unified **diff** "
    "patch that updates the Markdown spec. Only format as git diff."
)

### ───────────────────────── main loop ───────────────────────────────────── ###
def main():
    spec_text = SPEC_PATH.read_text()

    while True:
        # Ask one question
        question = ask_llm(
            [
                {"role": "system", "content": SYS_ASK},
                {"role": "user", "content": spec_text},
            ]
        )
        console.print(Panel(question, title="Clarifying Question", style="bold cyan", box=box.ROUNDED))

        answer = console.input("[bold green]Your answer (type /done to finish): [/]")
        if answer.strip().lower() == "/done":
            console.print("[yellow]Finished dialog. Exiting…[/]")
            break

        # Get patch
        diff = ask_llm(
            [
                {"role": "system", "content": SYS_PATCH},
                {"role": "user", "content": f"SPEC:\n{spec_text}\n\nANSWER:\n{answer}"},
            ]
        )
        console.print(Panel(diff, title="Proposed Patch", style="magenta"))

        # Apply patch crudely (for demo: append changes)
        SPEC_PATH.write_text(spec_text + "\n\n" + f"<!-- patched {datetime.utcnow().isoformat()} -->\n" + answer)
        spec_text = SPEC_PATH.read_text()

        console.print("[green]Patch applied![/]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted.[/]")
        sys.exit(1)