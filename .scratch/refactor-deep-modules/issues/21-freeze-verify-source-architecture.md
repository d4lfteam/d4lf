# 21 — Freeze and verify the source architecture

**What to build:** Produce a stable, behavior-preserving source architecture that is ready to become the permanent basis for the mirrored test tree.

**Blocked by:** 20 — Refactor tools and remove remaining dead source.

**Status:** ready-for-human

- [x] Every source Python file is at most 300 physical lines.
- [x] Total source Python LOC is at or below the corrected 26,229-line baseline, or an explicit
  offset is approved.
- [x] Every cross-package caller uses a package interface, and no compatibility shim remains.
- [x] Every source module has a clear capability owner and no known dead code remains.
- [x] All prek checks and the complete non-Selenium test suite pass.
- [ ] The source package structure is declared frozen before any test-tree restructuring begins.

## Audit

The structural source work is implemented, but this issue remains open until the stated freeze
gates are actually met. The source tree now has no files over 300 lines, no legacy capability
paths, and no cross-capability production imports through implementation modules. Importer Paragon
export is split behind the common `src.importing.paragon` module, while provider-specific Paragon
extraction stays in each provider package; Item, Perception, Application, and Overlay now own
the former shared seams.

The architecture-lock commit contained 26,229 source lines; the ADR's original 26,213 figure was
an undercount of 16. The current measured source total is 27,185 lines, 956 above that corrected
baseline. No dead or compatibility source was found by repository reference searches, Ruff, or
Vulture. The project owner approved this explicit 956-line offset on 2026-07-19, as recorded in
ADR 0006.

The 2026-07-19 acceptance audit confirms that `uv run prek run -a` passes all hooks and the complete
non-Selenium suite passes with 831 tests passed and 18 skipped. The source freeze remains open only
until the source budget is reconciled; it cannot be declared frozen while that decision is pending.
