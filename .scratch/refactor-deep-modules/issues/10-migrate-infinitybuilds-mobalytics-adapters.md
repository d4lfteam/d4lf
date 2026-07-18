# 10 — Migrate InfinityBuilds and Mobalytics adapters

**What to build:** Preserve InfinityBuilds and Mobalytics imports end to end through the normalized importing interface, including variants, filters, filenames, and Paragon output where available.

**Blocked by:** 08 — Establish the importing interface and shared pipeline.

**Status:** complete

- [x] Representative InfinityBuilds imports produce behaviorally equivalent profile and Paragon results.
- [x] Representative Mobalytics imports produce behaviorally equivalent profile and Paragon results.
- [x] Variant and filename-part selection remain unchanged for both sources.
- [x] Both adapters use shared importing behavior rather than duplicating it.
- [x] Every adapter source file is at most 300 physical lines.
- [x] Focused adapter tests and the line guard pass.

## Answer

InfinityBuilds and Mobalytics now live behind `src.importing.infinitybuilds` and
`src.importing.mobalytics` facades. Both adapters accept normalized `ImportRequest` values and
return `ImportResult` values through the shared pipeline, preserving source-specific filters,
variants, filename parts, custom filenames, and optional Paragon payloads. The legacy GUI adapter
modules were removed, and the importer window now listens to the capability-owned loggers.

Focused importing coverage passes (48 passed, 7 skipped), including final profile/result,
variant, filename, and Paragon assertions. The complete non-Selenium suite passes (620 passed,
47 skipped). Ruff and `ty` pass, and all touched adapter and focused test files are below 300
lines. The repository-wide line hook still reports unrelated pre-existing oversized modules,
which remain assigned to later refactor slices.

Implemented in rebased commit `937a09a`.
