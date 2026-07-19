# 26 — Complete integration coverage and acceptance

**What to build:** Demonstrate that the fully refactored application preserves D4LF behavior across deep-module interfaces, has an exact source-to-test map, passes every local quality gate, and still tests and packages successfully on Windows.

**Blocked by:** 22 — Mirror item, profile, and settings tests; 23 — Mirror importing, perception, and Paragon tests; 24 — Mirror automation, loot, and overlay tests; 25 — Mirror desktop, application, and tool tests.

**Status:** ready-for-human

- [x] Cross-capability scenarios are covered under the separate integration test tree through package interfaces.
- [x] Reusable case data is non-Python fixture data, and no unmapped Python helper module remains in the unit tree.
- [x] Every source module has exactly one mirrored unit-test file and every initializer maps to `init_test.py`.
- [x] The line guard, all prek checks, and the complete non-Selenium test suite pass locally.
- [ ] Source Python LOC remains at or below 26,213, and no temporary migration accommodation remains.
- [ ] Windows CI passes.
- [x] The separately triggered Windows executable build succeeds.

## Answer

Added mirrored coverage for `src/main.py` and `src/autoupdater.py`, an exact source-to-unit-test
parity guard, and public-facade integration scenarios for application composition, importing,
profiles, Paragon, perception, and item filtering. Reusable case data remains in the existing JSON
fixtures. The documented local gates pass: `uv run --no-project hooks/check_lines.py`, all 20
`prek` checks, and `uv run pytest . -m "not selenium" -v -n logical` (831 passed, 18 skipped).
`uv run python build.py` also succeeds on Windows for version 9.3.8.

Two acceptance items remain for human/repository coordination. Source Python measures 27,185
physical lines, which is 972 above the PRD's 26,213-line budget, and a local run cannot establish
that the hosted Windows CI workflow has passed.
