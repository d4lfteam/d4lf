______________________________________________________________________

## name: d4lf-verify description: Run d4lf validation in a disciplined, targeted way. Use after code changes, especially Python, UI, importer, overlay, lint, profile model, or packaging edits. Avoid this skill for purely textual documentation-only edits unless validation is relevant.

Validation order:

1. Prefer the narrowest relevant validation for the touched code.
1. Run lint first when the task is mainly code-shape, callback-signature, validator, or refactor related.
1. Run targeted tests before broad suites when the affected area is known.
1. Use the repository environment locally with `uv run ...` unless you are inside CI or the environment is already prepared.
1. Do not claim verification you did not actually run.

Suggested commands for this repo:

- `uv run ruff check <touched paths>`
- `uv run pytest <targeted tests> -v`
- `uv run pytest . -m "not selenium" -v -n logical`
- `prek run -a` for the full configured hook set when available
- `uv run python -m src.main` only when a task specifically requires a startup smoke check and the environment supports it

Common targeted examples:

- Profile model changes: `uv run ruff check src/config/profile_models.py tests/config/models_test.py` and `uv run pytest tests/config/models_test.py -v`
- Importer changes: `uv run ruff check src/gui/importer tests/gui/importer` and the relevant importer tests
- Overlay changes: `uv run ruff check src/paragon_overlay.py tests` plus the closest overlay or state tests

Output format:

- Commands run
- Pass/fail result for each command
- Anything not verified
- Whether remaining risk is low, medium, or high
