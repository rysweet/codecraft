import sys
import pathlib
import subprocess
import pytest

# Add src directory to path for importing bootstrap module
test_dir = pathlib.Path(__file__).resolve().parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

import bootstrap


def test_rebuild_flag(monkeypatch):
    """--rebuild should invoke ask_llm and overwrite script with generated code."""
    # Prepare fake file content for read_text (must contain top-level docstring)
    stub_content = '"""SPEC_DOC"""\nOLD CODE'
    # Track writes
    writes = []
    
    # Monkeypatch pathlib.Path.read_text to return stub_content
    monkeypatch.setattr(pathlib.Path, "read_text", lambda self: stub_content)
    # Monkeypatch ask_llm to return new code
    monkeypatch.setattr(bootstrap, "ask_llm", lambda prompt: "NEW GENERATED CODE")
    # Monkeypatch write_text to capture output
    monkeypatch.setattr(pathlib.Path, "write_text", lambda self, text: writes.append(text))

    # Call rebuild helper
    bootstrap.rebuild_from_spec()

    # Ensure the script was overwritten with the LLM response
    assert writes == ["NEW GENERATED CODE"]


def test_improve_flag(monkeypatch):
    """--improve should run N turns: auto_turn, rebuild, then pytest each turn."""
    calls = {"auto": [], "rebuild": 0, "pytest": 0, "writes": []}
    # Monkeypatch read_text to always provide a valid spec docstring section
    base_content = '"""SPEC1"""\nDUMMY'
    monkeypatch.setattr(pathlib.Path, "read_text", lambda self: base_content)
    # Monkeypatch write_text to record spec updates
    monkeypatch.setattr(pathlib.Path, "write_text", lambda self, text: calls["writes"].append(text))
    # Stub auto_turn to return a modified spec
    monkeypatch.setattr(bootstrap, "auto_turn", lambda spec, step: f"REFINED_SPEC_{step}")
    # Stub rebuild_from_spec to increment counter
    monkeypatch.setattr(bootstrap, "rebuild_from_spec", lambda: calls.__setitem__("rebuild", calls["rebuild"] + 1))
    # Stub subprocess.run to simulate pytest call
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.__setitem__("pytest", calls["pytest"] + 1))

    # Run the improve_tool with 3 turns
    bootstrap.improve_tool(3)

    # After 3 turns, rebuild and pytest should have been called 3 times each
    assert calls["rebuild"] == 3
    assert calls["pytest"] == 3
    # Spec document should have been rewritten each turn
    assert len(calls["writes"]) == 3
