# 24 — Mirror automation, loot, and overlay tests

**What to build:** Give contributors exact unit and package-interface test locations for automation, loot filtering modes, session statistics, and overlays while preserving platform-specific behavior.

**Blocked by:** 21 — Freeze and verify the source architecture.

**Status:** ready-for-agent

- [ ] Every automation, loot, statistics, and overlay source module has exactly one mirrored `<module>_test.py`.
- [ ] Every package initializer has a mirrored `init_test.py` that exercises meaningful interface behavior.
- [ ] Windows-only tests retain explicit platform handling rather than being silently weakened on macOS.
- [ ] Temporary source-phase imports and patch targets are removed.
- [ ] Unit tests assert observable behavior rather than extraction mechanics.
- [ ] Every Python test file in this slice is at most 300 physical lines, and focused tests pass.
