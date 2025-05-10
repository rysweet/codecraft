import os
import pytest
import boostrap

@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    reason="AZURE_OPENAI_ENDPOINT/DEPLOYMENT not set"
)
def test_live_azure_openai_connectivity():
    # log in (uses your CLI creds) and fire a simple 2+3 prompt
    boostrap.azure_cli_login()
    resp = boostrap.ask_llm([
        {"role":"system","content":"You are a calculator."},
        {"role":"user","content":"What is 2+3?"},
    ])
    assert resp and "5" in resp, f"Expected ‘5’ in response, got {resp}"
