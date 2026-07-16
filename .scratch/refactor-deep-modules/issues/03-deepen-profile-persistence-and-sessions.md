# 03 — Deepen profile persistence and sessions

**What to build:** Give maintainers one profile interface that validates, loads, saves, and edits profile documents while preserving user data and keeping profile sessions independent from PyQt.

**Blocked by:** 02 — Deepen item models and filtering.

**Status:** resolved

- [x] Existing profiles load and round-trip with unchanged canonical and backward-compatible fields.
- [x] Profile validation and document persistence are available through the package interface.
- [x] ProfileSession remains free of PyQt dependencies and preserves its established result behavior.
- [x] Profile, Paragon payload, and filename terminology matches the domain glossary.
- [x] No profile implementation file exceeds 300 physical lines.
- [ ] Focused profile tests and the line guard pass.

## Answer

`src.profiles` is now the sole cross-capability facade for profile models, document persistence,
Paragon values, and `ProfileSession` result types. The former `src.config.profile_*` modules were
removed without compatibility forwarding modules; private profile implementations are split into
cohesive modules below 300 lines. Production and test imports, type-only imports, dynamic module
references, and patch targets use the facade, including the `src.item` filtering callers.

Focused profile, importer, filter, and Paragon tests pass. The full non-Selenium suite passes:
589 passed, 47 skipped.
The repository-wide line guard remains blocked by pre-existing oversized modules outside this
slice, so its checklist item remains open.
