# 08 — Establish the importing interface and shared pipeline

**What to build:** Give users one normalized import flow that converts source-specific build guides into profile and Paragon results while hiding retries, browser setup, filter normalization, and filename assembly.

**Blocked by:** 02 — Deepen item models and filtering; 03 — Deepen profile persistence and sessions; 04 — Deepen settings and configuration.

**Status:** complete

- [x] Importers return one normalized result containing the selected variant, profile output, and optional Paragon payload.
- [x] Profile filename parts and custom profile filenames preserve their glossary-defined behavior.
- [x] Shared item, affix, rarity, filter, retry, and browser behavior is deduplicated behind the importing interface.
- [x] Source-specific adapters retain only source-specific extraction and normalization.
- [x] Shared importing source files are at most 300 physical lines.
- [x] Pipeline and shared importer tests pass.

## Answer

The new `src.importing` facade provides normalized `ImportRequest`, `ImportResult`, and
`ImportSource` contracts, URL-based source selection, and centralized filename assembly. The
import pipeline now returns the selected profile and optional typed Paragon payload while retaining
all saved variant filenames. Importer UI dispatch, retries, browser setup, filter conversion,
deduplication, profile activation, and source-independent conversions now use capability-owned
importing modules; the former GUI common module retains only shared GUI/source constants.

Focused importer tests pass (115 passed, 16 skipped), and the complete non-Selenium suite passes
(619 passed, 47 skipped). Ruff, ty, Python compilation, and diff checks pass. The repository-wide
line hook still reports the pre-existing oversized modules assigned to later refactor slices.

Implemented in rebased commit `0149465`.

### Structural review correction

Importing exposes one common `src.importing.paragon` module; provider-specific Paragon extraction
belongs in each provider package.
