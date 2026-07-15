# 23 — Mirror importing, perception, and Paragon tests

**What to build:** Give contributors an exact unit and package-interface test location for every importing, perception, and Paragon source module while preserving importer, parsing, geometry, and overlay behavior.

**Blocked by:** 21 — Freeze and verify the source architecture.

**Status:** ready-for-agent

- [ ] Every importing, perception, and Paragon source module has exactly one mirrored `<module>_test.py`.
- [ ] Every package initializer has a mirrored `init_test.py` that exercises meaningful interface behavior.
- [ ] Large importer and item-description case sets move to non-Python fixtures where appropriate.
- [ ] Duplicate tooltip and description tests are merged at the highest useful seam.
- [ ] Temporary source-phase imports and patch targets are removed.
- [ ] Every Python test file in this slice is at most 300 physical lines, and focused tests pass.
