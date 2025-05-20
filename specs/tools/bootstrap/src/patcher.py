"""
Module: patcher.py
Extracted diff/apply logic for Markdown spec patching.
Defines:
  - _apply_diff
  - apply_diff_direct
  - apply_semantic_patch
  - reorder_headings
  - apply_patch_pipeline
"""
from pathlib import Path
from unidiff import PatchSet, PatchedFile
import re
from rich.console import Console
from rich.panel import Panel
from unidiff.errors import UnidiffParseError

# Import prompt constant and LLM helper from bootstrap
from bootstrap import SYS_PENDING, ask_llm

console = Console()

# Re-import or copy original implementations here...
def _apply_diff(original: list[str], patch: PatchedFile) -> list[str] | None:
    # (Implementation moved from bootstrap)
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

# The rest of apply_diff_direct, apply_semantic_patch, reorder_headings,
# and apply_patch_pipeline would be copied here from bootstrap.py.
