import sys, pathlib
import pytest

test_dir = pathlib.Path(__file__).resolve().parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

import bootstrap as bs


def test_apply_semantic_patch_simple(tmp_path):
    # setup a simple spec file
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(
        "# Section 1\n"
        "Original content line.\n"
    )
    # create a diff to add a new line under Section 1
    diff_text = (
        "--- a/spec.md\n"
        "+++ b/spec.md\n"
        "@@ -1,2 +1,3 @@\n"
        " # Section 1\n"
        "+Inserted semantic line.\n"
        " Original content line.\n"
    )
    # apply semantic patch
    applied = bs.apply_semantic_patch(spec_file, diff_text)
    assert applied, "Semantic patch should apply successfully"
    result = spec_file.read_text().splitlines()
    # ensure the inserted line appears immediately after section header
    assert result[1] == "Inserted semantic line.", f"Unexpected content: {result}"


def test_apply_diff_direct_simple(tmp_path):
    spec_file = tmp_path / "spec2.md"
    spec_file.write_text(
        "foo\nbar\n"
    )
    diff_text = (
        "--- a/spec2.md\n"
        "+++ b/spec2.md\n"
        "@@ -1,2 +1,2 @@\n"
        " foo\n"
        "-bar\n"
        "+baz\n"
    )
    applied = bs.apply_diff_direct(spec_file, diff_text)
    assert applied, "Direct diff should apply"
    text = spec_file.read_text().splitlines()
    assert text == ["foo", "baz"]


def test_load_prompts_exist():
    # test that prompts load and are non-empty
    pm = bs.load_prompt('pm_ask')
    arch = bs.load_prompt('arch_answer')
    sys_p = bs.load_prompt('sys_patch')
    pending = bs.load_prompt('pending_patch')
    for name, content in [('pm_ask', pm), ('arch_answer', arch), ('sys_patch', sys_p), ('pending_patch', pending)]:
        assert content and len(content) > 10, f"Prompt {name} should not be empty"
