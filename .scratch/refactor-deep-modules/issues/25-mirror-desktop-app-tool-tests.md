# 25 — Mirror desktop, application, and tool tests

**What to build:** Give contributors exact unit and package-interface test locations for shared desktop behavior, application composition, startup, and developer tools.

**Blocked by:** 21 — Freeze and verify the source architecture.

**Status:** resolved

- [x] Every desktop, application, and tool source module has exactly one mirrored `<module>_test.py`.
- [x] The root and every package initializer have mirrored `init_test.py` coverage.
- [x] Startup, shell, widget, activity-log, update, replay, and data-generation behavior remains covered.
- [x] Temporary source-phase imports and patch targets are removed.
- [x] The unit tree contains only mirrored test files and conftest files.
- [x] Every Python test file in this slice is at most 300 physical lines, and focused tests pass.

## Answer

The application, desktop, and developer-tool test trees now mirror their source modules and
package facades. Legacy GUI, replay, data-loader, and UI-thread tests were consolidated at their
owning seams; application composition remains isolated under `tests/integration`, and unused
Python fixture modules were removed. The 300-line command is documented in `AGENTS.md`.

Validation passes with the line guard, all `prek` hooks, 821 non-Selenium tests passed, and 18
platform skips.
