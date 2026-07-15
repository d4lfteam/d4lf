# 03 — Deepen profile persistence and sessions

**What to build:** Give maintainers one profile interface that validates, loads, saves, and edits profile documents while preserving user data and keeping profile sessions independent from PyQt.

**Blocked by:** 02 — Deepen item models and filtering.

**Status:** ready-for-agent

- [ ] Existing profiles load and round-trip with unchanged canonical and backward-compatible fields.
- [ ] Profile validation and document persistence are available through the package interface.
- [ ] ProfileSession remains free of PyQt dependencies and preserves its established result behavior.
- [ ] Profile, Paragon payload, and filename terminology matches the domain glossary.
- [ ] No profile implementation file exceeds 300 physical lines.
- [ ] Focused profile tests and the line guard pass.
