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
