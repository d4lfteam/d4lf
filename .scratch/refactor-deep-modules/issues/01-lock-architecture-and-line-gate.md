# 01 — Lock architecture and line gate

**What to build:** Establish the refactor contract that lets later capability slices move code safely: every source module has an owner, every deep module has a small interface, line and source-size baselines are explicit, and contributors can run the new guard through the documented validation workflow.

**Blocked by:** None — can start immediately.

**Type:** task

**Status:** resolved

- [x] Every source Python module is assigned to a capability and classified as keep, move, split, or delete.
- [x] Each capability has an agreed package interface and cross-package implementation imports are prohibited.
- [x] High-risk importer, perception, overlay, and desktop seams are compared through at least two interface designs.
- [x] An ADR records the capability-first deep-module decision and its trade-offs.
- [x] The line guard is documented with the normal repository validation commands.
- [x] The 26,213-line source baseline and current behavioral baseline are recorded without overwriting existing user changes.

## Answer

`docs/adr/0006-capability-first-deep-module-architecture.md` defines the capability facades,
cross-package import rule, four high-risk seam comparisons, and an exact 108-module migration
inventory. It records the 26,213-line source baseline and the macOS behavioral baseline of 586
passed and 47 skipped non-Selenium tests.

`README.md` documents the normal `uv run prek run -a` and complete non-Selenium pytest workflow,
plus its focused line-gate command. The pre-existing user-owned `hooks/check_lines.py` and
`prek.toml` changes were preserved. The complete non-Selenium suite passes; the line gate correctly
reports the 29 source and 8 test migrations that the later refactor slices must complete.
