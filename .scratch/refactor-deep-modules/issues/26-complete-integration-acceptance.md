# 26 — Complete integration coverage and acceptance

**What to build:** Demonstrate that the fully refactored application preserves D4LF behavior across deep-module interfaces, has an exact source-to-test map, passes every local quality gate, and still tests and packages successfully on Windows.

**Blocked by:** 22 — Mirror item, profile, and settings tests; 23 — Mirror importing, perception, and Paragon tests; 24 — Mirror automation, loot, and overlay tests; 25 — Mirror desktop, application, and tool tests.

**Status:** ready-for-agent

- [ ] Cross-capability scenarios are covered under the separate integration test tree through package interfaces.
- [ ] Reusable case data is non-Python fixture data, and no unmapped Python helper module remains in the unit tree.
- [ ] Every source module has exactly one mirrored unit-test file and every initializer maps to `init_test.py`.
- [ ] The line guard, all prek checks, and the complete non-Selenium test suite pass locally.
- [ ] Source Python LOC remains at or below 26,213, and no temporary migration accommodation remains.
- [ ] Windows CI passes.
- [ ] The separately triggered Windows executable build succeeds.
