# 09 — Migrate D4Builds and Maxroll adapters

**What to build:** Preserve D4Builds and Maxroll imports end to end through the normalized importing interface, including variants, filters, filenames, and Paragon output where available.

**Blocked by:** 08 — Establish the importing interface and shared pipeline.

**Status:** complete

- [x] Representative D4Builds imports produce behaviorally equivalent profile and Paragon results.
- [x] Representative Maxroll imports produce behaviorally equivalent profile and Paragon results.
- [x] Variant and filename-part selection remain unchanged for both sources.
- [x] Both adapters use shared importing behavior rather than duplicating it.
- [x] Every adapter source file is at most 300 physical lines.
- [x] Focused adapter tests and the adapter line checks pass.

## Answer

D4Builds and Maxroll now live behind source-specific importing subpackage facades:
`src.importing.d4builds` and `src.importing.maxroll`. Their adapters accept normalized
`ImportRequest` values and return `ImportResult` values through the shared importing pipeline.
Extraction, planner/item conversion, metadata, filename handling, variants, filters, retries, and
optional Paragon export preserve the previous behavior without GUI-path compatibility modules.

The shared pipeline, importing configuration, and Paragon export implementation now live under
`src.importing`; remaining source adapters were updated to use the relocated shared pipeline.

Focused adapter tests pass (46 passed, 18 deselected), and the complete non-Selenium suite passes
(620 passed, 47 skipped). Ruff and ty pass. Every new D4Builds/Maxroll source file is at most 300
physical lines. The repository-wide line hook still reports pre-existing oversized modules, plus
shared `paragon_export.py` and later-ticket adapter files assigned to subsequent migration slices.

Implemented in rebased commit `d977159`.
