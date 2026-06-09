______________________________________________________________________

## name: d4lf-lint-safe-edit description: Make d4lf code changes that stay compatible with the repo's strict Ruff setup. Use when editing Python code in areas likely to trigger Ruff issues such as callbacks, exception handling, imports, comments, validators, or small refactors.

1. Check the current `pyproject.toml` before relying on remembered Ruff ignores or rules.
1. Assume strict Ruff with `select = ["ALL"]` and preview rules enabled unless the current config says otherwise.
1. Avoid known failure patterns already called out in AGENTS.md.
1. Prefer explicit, simple control flow over clever compact code.
1. Keep imports normal and module-level when practical; use lazy imports only when needed for circular imports or startup cost already documented in the file.
1. Do not introduce unused parameters, dead helpers, one-line helper functions used only once, or broad exception patterns.
1. Keep comments/docstrings helpful but restrained.
1. After edits, run targeted Ruff on the touched paths when the environment supports it.
1. If a design choice was made mainly for lint compatibility, mention it briefly in the summary.
