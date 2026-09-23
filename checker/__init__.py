"""Checkout Auditor checker: pure-Python checks and scoring over one run record.

Import directly from the modules (`from checker.checks import check_run`,
`from checker.score import score_run, load_key_for`) or lazily via this package.
"""
import importlib

_EXPORTS = {
    "check_run": "checker.checks",
    "normalise_label": "checker.checks",
    "is_charge_label": "checker.checks",
    "match_lines": "checker.checks",
    "score_run": "checker.score",
    "load_key_for": "checker.score",
    "match_findings_to_traps": "checker.score",
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name in _EXPORTS:
        return getattr(importlib.import_module(_EXPORTS[name]), name)
    raise AttributeError(f"module 'checker' has no attribute {name!r}")
