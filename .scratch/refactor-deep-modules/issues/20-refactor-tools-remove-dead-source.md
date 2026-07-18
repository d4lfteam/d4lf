# 20 — Refactor tools and remove remaining dead source

**What to build:** Preserve replay and data-generation workflows while completing a repository-wide contraction that removes obsolete source paths, duplicate helpers, and abstractions that no longer earn their interface.

**Blocked by:** 13 — Deepen screenshot and tooltip perception; 19 — Complete desktop shell and application composition.

**Status:** resolved

- [x] Replay tools produce equivalent results through final capability interfaces.
- [x] Data generation preserves its current inputs, outputs, and validation behavior.
- [x] Every tool source Python file is at most 300 physical lines.
- [x] Repository-wide references, dynamic entry points, build configuration, and Windows-only usage are checked before deletion.
- [x] No compatibility forwarding module, obsolete helper, or unused source symbol remains.
- [x] Focused tool tests and the line guard pass.

## Answer

Replay and data-generation tools now live behind the `src.tools.replay` and
`src.tools.data_generation` subpackages. Replay rendering and diagnostics are split into cohesive
modules, and data-generation parsing, affix handling, and dataset generation no longer depend on
oversized flat modules. The old flat tool modules, unused random-number helper, and unreachable
`OpenUserConfigButton` modules were removed after repository-wide reference and packaging checks.

The documented data-generation workflow now uses `uv run python -m src.tools.data_generation` and
retains the repository-relative default d4data path. Focused tool tests pass (27 tests), all tool
source files are below 300 lines, and the complete non-Selenium suite passes (688 passed, 16
skipped on macOS).
