# 25 — Mirror desktop, application, and tool tests

**What to build:** Give contributors exact unit and package-interface test locations for shared desktop behavior, application composition, startup, and developer tools.

**Blocked by:** 21 — Freeze and verify the source architecture.

**Status:** ready-for-agent

- [ ] Every desktop, application, and tool source module has exactly one mirrored `<module>_test.py`.
- [ ] The root and every package initializer have mirrored `init_test.py` coverage.
- [ ] Startup, shell, widget, activity-log, update, replay, and data-generation behavior remains covered.
- [ ] Temporary source-phase imports and patch targets are removed.
- [ ] The unit tree contains only mirrored test files and conftest files.
- [ ] Every Python test file in this slice is at most 300 physical lines, and focused tests pass.
