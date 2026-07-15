# 22 — Mirror item, profile, and settings tests

**What to build:** Give contributors an exact, predictable unit and package-interface test location for every item, profile, and settings source module while preserving the established behavior baseline.

**Blocked by:** 21 — Freeze and verify the source architecture.

**Status:** ready-for-agent

- [ ] Every item, profile, and settings source module has exactly one mirrored `<module>_test.py`.
- [ ] Every package initializer has a mirrored `init_test.py` that exercises meaningful interface behavior.
- [ ] Existing tests are renamed, moved, split, and deduplicated without weakening assertions.
- [ ] Temporary source-phase imports and patch targets are replaced by final references.
- [ ] Reusable case data is stored as non-Python fixtures rather than extra Python helper modules.
- [ ] Every Python test file in this slice is at most 300 physical lines, and focused tests pass.
