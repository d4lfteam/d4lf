# 20 — Refactor tools and remove remaining dead source

**What to build:** Preserve replay and data-generation workflows while completing a repository-wide contraction that removes obsolete source paths, duplicate helpers, and abstractions that no longer earn their interface.

**Blocked by:** 13 — Deepen screenshot and tooltip perception; 19 — Complete desktop shell and application composition.

**Status:** ready-for-agent

- [ ] Replay tools produce equivalent results through final capability interfaces.
- [ ] Data generation preserves its current inputs, outputs, and validation behavior.
- [ ] Every tool source Python file is at most 300 physical lines.
- [ ] Repository-wide references, dynamic entry points, build configuration, and Windows-only usage are checked before deletion.
- [ ] No compatibility forwarding module, obsolete helper, or unused source symbol remains.
- [ ] Focused tool tests and the line guard pass.
