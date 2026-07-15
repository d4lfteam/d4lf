# 04 — Deepen settings and configuration

**What to build:** Give users unchanged settings behavior through a cohesive interface for typed values, persistence, reload decisions, UI coordinates, and hotkey bindings.

**Blocked by:** 01 — Lock architecture and line gate.

**Status:** ready-for-agent

- [ ] Settings load, save, defaults, and reload-group behavior remain unchanged.
- [ ] Hotkey bindings preserve their stable human-readable vocabulary and validation rules.
- [ ] Resolution-scaled UI coordinates preserve their current reference behavior.
- [ ] Callers use the settings package interface rather than persistence implementation details.
- [ ] Windows-specific and cross-platform settings behavior remain available.
- [ ] No settings implementation file exceeds 300 physical lines, and focused tests pass.
