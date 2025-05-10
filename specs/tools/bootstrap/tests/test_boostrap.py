import sys
import pathlib
import pytest

# Add src directory to path for importing boostrap module
test_dir = pathlib.Path(__file__).resolve().parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

import os
import boostrap
import pytest
from unidiff import PatchSet


def test_apply_diff_simple():
    original = ["foo\n", "bar\n", "qux\n"]
    diff_text = (
        "--- a/a.txt\n"
        "+++ b/a.txt\n"
        "@@ -1,3 +1,3 @@\n"
        " foo\n"
        "-bar\n"
        "+baz\n"
        " qux\n"
    )
    patchset = PatchSet(diff_text.splitlines(keepends=True))
    patched = boostrap._apply_diff(original, patchset[0])
    assert patched == ["foo\n", "baz\n", "qux\n"]


def test_apply_diff_failure():
    original = ["foo\n", "bar\n"]
    diff_text = (
        "--- a/a.txt\n"
        "+++ b/a.txt\n"
        "@@ -1,2 +1,2 @@\n"
        " foo\n"
        "-baz\n"
        "+qux\n"
    )
    patchset = PatchSet(diff_text.splitlines(keepends=True))
    patched = boostrap._apply_diff(original, patchset[0])
    # Removal of non-existent line 'baz' still produces a patch replacing removal with 'qux'
    assert patched == ["foo\n", "qux\n"]


def test_reorder_headings():
    text = "Intro\n# Zebra\nContent\n# apple\nMore"
    result = boostrap.reorder_headings(text)
    # Headings sorted case-insensitive: apple comes before Zebra
    assert result.startswith("Intro")
    assert "# apple" in result
    assert result.index("# apple") < result.index("# Zebra")


def test_apply_patch_pipeline_direct(tmp_path, capsys):
    # Create a temporary spec file
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("foo\nbar\n")
    # Diff to change 'bar' to 'baz'
    diff_text = (
        "--- a/spec.md\n"
        "+++ b/spec.md\n"
        "@@ -1,2 +1,2 @@\n"
        " foo\n"
        "-bar\n"
        "+baz\n"
    )
    boostrap.apply_patch_pipeline(spec_file, diff_text)
    content = spec_file.read_text()
    assert "baz\n" in content
    assert "bar\n" not in content
    captured = capsys.readouterr()
    assert "patch applied (direct)" in captured.out


def test_ask_llm(monkeypatch, capsys):
    # Dummy classes to simulate AzureOpenAI response
    class DummyMessage:
        def __init__(self, content):
            self.content = content

    class DummyChoice:
        def __init__(self, content):
            self.message = DummyMessage(content)

    class DummyResponse:
        def __init__(self, content):
            self.choices = [DummyChoice(content)]

    def dummy_create(model, messages, max_completion_tokens):
        return DummyResponse("  hello world  ")

    # Monkeypatch the client's chat completion method
    monkeypatch.setattr(boostrap.client.chat.completions, "create", dummy_create)
    result = boostrap.ask_llm([{"role": "user", "content": "hi"}])
    # Verify return value is trimmed
    assert result == "hello world"
    # Verify styled logging panels were printed
    captured = capsys.readouterr()
    out = captured.out
    assert "Prompt Payload" in out
    assert "LLM Response" in out


def test_auto_turn(monkeypatch, tmp_path):
    # Setup a temporary spec file and monkeypatch SPEC_PATH
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("initial\n")
    monkeypatch.setattr(boostrap, "SPEC_PATH", spec_file)

    # Prepare fake responses for ask_llm: question, answer, diff
    responses = ["Q", "A", (
        "--- a/spec.md\n"
        "+++ b/spec.md\n"
        "@@ -1 +1 @@\n"
        "-initial\n"
        "+updated\n"
    )]
    call_count = {"count": 0}

    def fake_ask_llm(messages):
        res = responses[call_count["count"]]
        call_count["count"] += 1
        return res

    monkeypatch.setattr(boostrap, "ask_llm", fake_ask_llm)

    new_spec = boostrap.auto_turn("initial\n")
    assert new_spec == "updated\n"
    # ensure SPEC_PATH was updated
    assert spec_file.read_text() == "updated\n"
    

def test_apply_patch_pipeline_smart(monkeypatch, tmp_path, capsys):
    # Force direct diff to fail to test smart insert branch
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("foo\nbar\nqux\n")
    diff_text = (
        "--- a/spec.md\n"
        "+++ b/spec.md\n"
        "@@ -1,3 +1,4 @@\n"
        " foo\n"
        " bar\n"
        "+baz\n"
        " qux\n"
    )
    # Monkeypatch direct apply to return None
    monkeypatch.setattr(boostrap, "_apply_diff", lambda original, target: None)
    boostrap.apply_patch_pipeline(spec_file, diff_text)
    # Smart insert should have added 'baz' before 'foo' (context match at first line)
    lines = spec_file.read_text().splitlines()
    assert lines == ["baz", "foo", "bar", "qux"]
    captured = capsys.readouterr()
    assert "smart insert" in captured.out.lower()

def test_apply_patch_pipeline_fallback(monkeypatch, tmp_path, capsys):
    # Force both direct and smart insert to fail to test fallback branch
    spec_file = tmp_path / "spec.md"
    # Spec with unsorted headings
    spec_file.write_text("Intro\n# Zebra\nZ text\n# apple\nA text\n")
    diff_text = (
        "--- a/spec.md\n"
        "+++ b/spec.md\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    # Monkeypatch direct apply and smart insert to fail
    monkeypatch.setattr(boostrap, "_apply_diff", lambda original, target: None)
    # Smart insert will break on missing context
    boostrap.apply_patch_pipeline(spec_file, diff_text)
    # After fallback, headings should be reordered case-insensitively
    content = spec_file.read_text().splitlines()
    assert content[0] == "Intro"
    headings = [l for l in content if l.startswith("#")]
    assert headings == ["# apple", "# Zebra"]
    captured = capsys.readouterr()
    assert "append" in captured.out.lower()
    assert "reordered" in captured.out.lower()
import os
import pytest
import boostrap

@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    reason="Azure OpenAI env vars not set, skipping live integration test"
)
def test_live_azure_openai_connectivity():
    """
    End-to-end integration: send a simple prompt to Azure OpenAI.
    Requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT set.
    """
    # Perform Azure CLI login with existing credentials
    boostrap.azure_cli_login()
    # Send a simple math prompt
    prompt = [
        {"role": "system", "content": "You are a calculator."},
        {"role": "user", "content": "What is 2+3?"},
    ]
    response = boostrap.ask_llm(prompt)
    assert response, "No response received from Azure OpenAI"
    assert "5" in response, f"Unexpected response: {response}"
