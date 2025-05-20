"""
Bootstrap patching module.
Exports:
  - _apply_diff
  - apply_diff_direct
  - apply_semantic_patch
  - reorder_headings
  - apply_patch_pipeline
"""
from .patcher import (
    _apply_diff,
    apply_diff_direct,
    apply_semantic_patch,
    reorder_headings,
    apply_patch_pipeline,
)
