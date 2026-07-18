# 22 — Mirror item, profile, and settings tests

**What to build:** Give contributors an exact, predictable unit and package-interface test location for every item, profile, and settings source module while preserving the established behavior baseline.

**Blocked by:** 21 — Freeze and verify the source architecture.

**Status:** ready-for-human

- [x] Every item, profile, and settings source module has exactly one mirrored `<module>_test.py`.
- [x] Every package initializer has a mirrored `init_test.py` that exercises meaningful interface behavior.
- [x] Existing tests are renamed, moved, split, and deduplicated without weakening assertions.
- [x] Temporary source-phase imports and patch targets are replaced by final references.
- [x] Reusable case data is stored as non-Python fixtures rather than extra Python helper modules.
- [x] Every Python test file in this slice is at most 300 physical lines, and focused tests pass.

## Answer

The item, profile, and settings unit trees now mirror every source module and package initializer.
Legacy tests moved from `config`, `gui`, and `utils` into their owning capability paths, while
filter cases moved from Python helper modules into `tests/item/filter/data/fixtures.json` with a
shared loader. Shared filter and settings fixtures are centralized in `conftest.py`, and package
and module mirrors assert public exports or observable behavior.

Validation passes for the affected manifest (394 tests), Ruff, `ty`, and the complete non-Selenium
suite (738 passed, 16 skipped). The repository line hook still reports four pre-existing files
owned by perception/importer follow-up issues 23 and 25; no changed file in this slice exceeds 300
lines.
