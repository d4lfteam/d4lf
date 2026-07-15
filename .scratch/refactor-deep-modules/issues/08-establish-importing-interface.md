# 08 — Establish the importing interface and shared pipeline

**What to build:** Give users one normalized import flow that converts source-specific build guides into profile and Paragon results while hiding retries, browser setup, filter normalization, and filename assembly.

**Blocked by:** 02 — Deepen item models and filtering; 03 — Deepen profile persistence and sessions; 04 — Deepen settings and configuration.

**Status:** ready-for-agent

- [ ] Importers return one normalized result containing the selected variant, profile output, and optional Paragon payload.
- [ ] Profile filename parts and custom profile filenames preserve their glossary-defined behavior.
- [ ] Shared item, affix, rarity, filter, retry, and browser behavior is deduplicated behind the importing interface.
- [ ] Source-specific adapters retain only source-specific extraction and normalization.
- [ ] Shared importing source files are at most 300 physical lines.
- [ ] Pipeline and shared importer tests pass.
