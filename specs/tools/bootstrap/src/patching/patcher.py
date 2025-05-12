"""
patching/patcher.py

Standalone module for spec diff/patch functionality.
Exports:
  - _apply_diff
  - apply_diff_direct
  - apply_semantic_patch
  - reorder_headings
  - apply_patch_pipeline
"""
import pathlib, re
from unidiff import PatchSet, PatchedFile
from unidiff.errors import UnidiffParseError
from rich.console import Console
from rich.panel import Panel

"""
Note: Avoid circular imports by deferring bootstrap imports inside functions.
"""

console = Console()

def _apply_diff(original: list[str], patch: PatchedFile) -> list[str] | None:
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


def apply_diff_direct(spec_path: pathlib.Path, diff_text: str) -> bool:
    """Attempt direct and smart insert without fallback; return True if applied."""
    try:
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
        return False


def apply_semantic_patch(spec_path: pathlib.Path, diff_text: str) -> bool:
    """Delegate semantic patch to the bootstrap module's implementation."""
    # import here to avoid circular module load
    from bootstrap import apply_semantic_patch as _sem_patch
    return _sem_patch(spec_path, diff_text)


def reorder_headings(md_text: str) -> str:
    parts = re.split(r"(?m)^# (.+)$", md_text)
    intro = parts[0]
    titled = list(zip(parts[1::2], parts[2::2]))
    titled.sort(key=lambda t: t[0].lower())
    return intro + "".join(f"# {h}{b}" for h, b in titled)


def apply_patch_pipeline(spec_path: pathlib.Path, diff_text: str) -> None:
    # Wrap original function for consistency; import from bootstrap
    from bootstrap import apply_patch_pipeline as _orig
    _orig(spec_path, diff_text)
