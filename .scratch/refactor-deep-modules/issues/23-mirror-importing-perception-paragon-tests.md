# 23 — Mirror importing, perception, and Paragon tests

**What to build:** Give contributors an exact unit and package-interface test location for every importing, perception, and Paragon source module while preserving importer, parsing, geometry, and overlay behavior.

**Blocked by:** 21 — Freeze and verify the source architecture.

**Status:** resolved

- [x] Every importing, perception, and Paragon source module has exactly one mirrored `<module>_test.py`.
- [x] Every package initializer has a mirrored `init_test.py` that exercises meaningful interface behavior.
- [x] Large importer and item-description case sets move to non-Python fixtures where appropriate.
- [x] Duplicate tooltip and description tests are merged at the highest useful seam.
- [x] Temporary source-phase imports and patch targets are removed.
- [x] Every Python test file in this slice is at most 300 physical lines, and focused tests pass.

## Answer

The importing, perception, and Paragon unit trees now mirror every source module and package
initializer. Existing importer, tooltip, geometry, TTS, and Paragon tests were relocated to their
capability seams, while importer coverage was split by adapter implementation. The 31 item-text
cases now live in `tests/perception/data/parser_cases.json` and are exercised through the parser
seam. Duplicate geometry/tooltip diagnostics were consolidated, and cross-capability tests use
public facades rather than private Item implementation paths.

Focused validation passes with 247 tests passed and 17 skipped. The complete non-Selenium suite
passes with 757 tests passed and 17 skipped. `uv run prek run -a`, `ty`, the line gate, and the
mirror parity audit pass. Implemented in commit `b9326ca`.

The mirror tracks perception subpackages and the single common importing Paragon module; provider
Paragon tests remain under their provider packages.
