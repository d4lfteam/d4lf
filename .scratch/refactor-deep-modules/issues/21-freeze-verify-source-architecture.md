# 21 — Freeze and verify the source architecture

**What to build:** Produce a stable, behavior-preserving source architecture that is ready to become the permanent basis for the mirrored test tree.

**Blocked by:** 20 — Refactor tools and remove remaining dead source.

**Status:** ready-for-agent

- [ ] Every source Python file is at most 300 physical lines.
- [ ] Total source Python LOC is at or below the 26,213-line baseline.
- [ ] Every cross-package caller uses a package interface, and no compatibility shim remains.
- [ ] Every source module has a clear capability owner and no known dead code remains.
- [ ] All prek checks and the complete non-Selenium test suite pass.
- [ ] The source package structure is declared frozen before any test-tree restructuring begins.

## Audit

The structural source work is implemented, but this issue remains open until the stated freeze
gates are actually met. The source tree now has no files over 300 lines, no legacy capability
paths, and no cross-capability production imports through implementation modules. Importer Paragon
export is split behind `src.importing.paragon`; Item, Perception, Application, and Overlay now own
the former shared seams. The non-Selenium suite passes with 688 passed and 16 skipped, and `ty`
passes.

The measured source total is 27,185 lines versus the 26,213-line ceiling. `uv run prek run -a`
therefore still fails only its repository-wide test line gate, which reports the seven oversized
test files assigned to issues 22 and 25; all other hooks pass. The source freeze and status remain
open until the source budget is reconciled and the test-tree gate is completed.
