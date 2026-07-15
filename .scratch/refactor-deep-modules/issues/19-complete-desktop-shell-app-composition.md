# 19 — Complete desktop shell and application composition

**What to build:** Let users start D4LF and access profiles, settings, importing, Paragon, loot modes, activity information, updates, and shutdown through one desktop shell wired only to capability interfaces.

**Blocked by:** 07 — Complete the profile editor shell; 11 — Complete importer UI and Paragon export; 14 — Deepen the Paragon capability; 16 — Deepen loot filtering modes; 17 — Deepen session statistics and boss overlay; 18 — Consolidate shared desktop primitives.

**Status:** ready-for-agent

- [ ] Main startup, logging, update checks, startup messages, and shutdown preserve current behavior.
- [ ] Unified and standalone windows preserve navigation, settings, profile, importer, and close-event behavior.
- [ ] Application composition depends on package interfaces rather than implementation modules.
- [ ] Capability-specific GUI code is not pulled back into the desktop shell.
- [ ] Every application and shell source Python file is at most 300 physical lines.
- [ ] Focused startup and desktop-shell tests pass.
