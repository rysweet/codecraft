import sys
import pathlib
import pytest

# Add src directory to path for importing boostrap module
test_dir = pathlib.Path(__file__).resolve().parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

import boostrap
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


def test_ask_llm(monkeypatch):
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
    assert result == "hello world"


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

def test_integration_azure_login_and_client_init(monkeypatch, tmp_path):
    # Arrange environment variables for Azure and OpenAI
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant123")
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "sub456")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://endpoint")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "deploy789")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "api123")

    # Capture subprocess.run calls for Azure CLI login and subscription set
    import subprocess
    calls = []
    def fake_run(cmd, check=True):
        calls.append(cmd)
    monkeypatch.setattr(subprocess, "run", fake_run)

    # Inject dummy azure.identity module if missing
    import sys, types
    azure_mod = types.ModuleType('azure')
    identity_mod = types.ModuleType('azure.identity')
    azure_mod.identity = identity_mod
    sys.modules['azure'] = azure_mod
    sys.modules['azure.identity'] = identity_mod
    # Monkeypatch Azure identity credential and token provider
    import azure.identity as identity
    # Allow setting attributes even if they don't exist yet
    monkeypatch.setattr(identity, "DefaultAzureCredential", lambda: "cred", raising=False)
    monkeypatch.setattr(identity, "get_bearer_token_provider", lambda cred, scope: "provider", raising=False)

    # Dummy AzureOpenAI to capture init parameters
    init_args = {}
    # Inject dummy openai module if missing
    openai_mod = types.ModuleType('openai')
    sys.modules['openai'] = openai_mod
    import openai
    class DummyAzureOpenAI:
        def __init__(self, azure_endpoint, api_version, azure_ad_token_provider):
            init_args['endpoint'] = azure_endpoint
            init_args['version'] = api_version
            init_args['provider'] = azure_ad_token_provider
        # Minimal chat interface to avoid attribute errors
        @property
        def chat(self):
            class C: pass
            C.completions = type('X', (), {'create': staticmethod(lambda **kwargs: None)})
            return C()
    monkeypatch.setattr(openai, "AzureOpenAI", DummyAzureOpenAI)

    # Reload boostrap module to re-execute top-level init code
    import importlib, boostrap
    importlib.reload(boostrap)
    # Invoke Azure CLI login explicitly (moved into azure_cli_login)
    boostrap.azure_cli_login()

    # Assert Azure CLI invoked for login and account set
    assert ['az', 'login', '--tenant', 'tenant123'] in calls
    assert ['az', 'account', 'set', '--subscription', 'sub456'] in calls

    # Assert AzureOpenAI was initialized with expected values
    assert init_args['endpoint'] == 'https://endpoint'
    assert init_args['version'] == 'api123'
    assert init_args['provider'] == 'provider'

def test_integration_with_env_file(monkeypatch, tmp_path):
    # Simulate running from repo root with a .codecraft/.env file
    monkeypatch.chdir(tmp_path)
    craft_dir = tmp_path / ".codecraft"
    craft_dir.mkdir()
    env_file = craft_dir / ".env"
    env_file.write_text(
        "AZURE_TENANT_ID=tenX\n"
        "AZURE_SUBSCRIPTION_ID=subY\n"
        "AZURE_OPENAI_ENDPOINT=https://ep\n"
        "AZURE_OPENAI_DEPLOYMENT=depZ\n"
        "AZURE_OPENAI_API_VERSION=v1\n"
    )
    # Stub subprocess.run to capture Azure CLI calls
    import subprocess
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, check=True: calls.append(cmd))
    # Stub azure.identity module
    import sys, types
    azure_pkg = types.ModuleType("azure")
    identity_mod = types.ModuleType("azure.identity")
    identity_mod.DefaultAzureCredential = lambda: "cred2"
    identity_mod.get_bearer_token_provider = lambda cred, scope: "prov2"
    azure_pkg.identity = identity_mod
    sys.modules["azure"] = azure_pkg
    sys.modules["azure.identity"] = identity_mod
    # Stub openai.AzureOpenAI client
    openai_pkg = types.ModuleType("openai")
    init_args2 = {}
    class DummyClient2:
        def __init__(self, azure_endpoint, api_version, azure_ad_token_provider):
            init_args2['endpoint'] = azure_endpoint
            init_args2['version'] = api_version
            init_args2['provider'] = azure_ad_token_provider
        @property
        def chat(self):
            class C: pass
            C.completions = type('Y', (), {'create': staticmethod(lambda **k: None)})
            return C()
    openai_pkg.AzureOpenAI = DummyClient2
    sys.modules["openai"] = openai_pkg
    # Reload module to apply new .env and stubs
    import importlib, boostrap
    importlib.reload(boostrap)
    # Invoke Azure CLI login (now in azure_cli_login)
    boostrap.azure_cli_login()
    # Validate Azure CLI calls
    assert ['az', 'login', '--tenant', 'tenX'] in calls
    assert ['az', 'account', 'set', '--subscription', 'subY'] in calls
    # Validate client settings from .env
    assert init_args2['endpoint'] == 'https://ep'
    assert init_args2['version'] == 'v1'
    assert init_args2['provider'] == 'prov2'
    
    # Test that ask_llm uses the initialized client to call LLM and trim response
    # Replace chat completion to return a padded content
    class DummyMsg:
        def __init__(self, content): self.content = content
    class DummyChoice:
        def __init__(self, content): self.message = DummyMsg(content)
    class DummyResp:
        def __init__(self, content): self.choices = [DummyChoice(content)]
    # Monkeypatch the create method on the existing client instance
    monkeypatch.setattr(boostrap.client.chat.completions, 'create', lambda **kwargs: DummyResp('  integrated  '))
    result = boostrap.ask_llm([{"role": "user", "content": "hi"}])
    assert result == 'integrated'
    
def test_integration_with_env_file(monkeypatch, tmp_path):
    # Simulate repo root with .codecraft/.env file containing Azure settings
    monkeypatch.chdir(tmp_path)
    craft_dir = tmp_path / ".codecraft"
    craft_dir.mkdir()
    env_file = craft_dir / ".env"
    env_file.write_text(
        "AZURE_TENANT_ID=tenX\n"
        "AZURE_SUBSCRIPTION_ID=subY\n"
        "AZURE_OPENAI_ENDPOINT=https://ep\n"
        "AZURE_OPENAI_DEPLOYMENT=depZ\n"
        "AZURE_OPENAI_API_VERSION=v1\n"
    )
    # Capture CLI calls
    import subprocess
    calls = []
    def fake_run(cmd, check=True):
        calls.append(cmd)
    monkeypatch.setattr(subprocess, "run", fake_run)
    # Patch Azure identity and OpenAI client
    import azure.identity as identity, openai
    monkeypatch.setattr(identity, "DefaultAzureCredential", lambda: "cred2")
    monkeypatch.setattr(identity, "get_bearer_token_provider", lambda c, s: "prov2")
    init_args2 = {}
    class DummyClient2:
        def __init__(self, azure_endpoint, api_version, azure_ad_token_provider):
            init_args2['endpoint'] = azure_endpoint
            init_args2['version'] = api_version
            init_args2['provider'] = azure_ad_token_provider
        @property
        def chat(self):
            class C: pass
            C.completions = type('Y', (), {'create': staticmethod(lambda **k: None)})
            return C()
    monkeypatch.setattr(openai, "AzureOpenAI", DummyClient2)
    # Reload module to pick up .env and re-run Azure setup
    import importlib, boostrap
    importlib.reload(boostrap)
    # Validate CLI calls from .env values
    assert ['az', 'login', '--tenant', 'tenX'] in calls
    assert ['az', 'account', 'set', '--subscription', 'subY'] in calls
    # Validate client init from .env
    assert init_args2['endpoint'] == 'https://ep'
    assert init_args2['version'] == 'v1'
    assert init_args2['provider'] == 'prov2'
