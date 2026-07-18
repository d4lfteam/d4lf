# 19 — Complete desktop shell and application composition

**What to build:** Let users start D4LF and access profiles, settings, importing, Paragon, loot modes, activity information, updates, and shutdown through one desktop shell wired only to capability interfaces.

**Blocked by:** 07 — Complete the profile editor shell; 11 — Complete importer UI and Paragon export; 14 — Deepen the Paragon capability; 16 — Deepen loot filtering modes; 17 — Deepen session statistics and boss overlay; 18 — Consolidate shared desktop primitives.

**Status:** resolved

- [x] Main startup, logging, update checks, startup messages, and shutdown preserve current behavior.
- [x] Unified and standalone windows preserve navigation, settings, profile, importer, and close-event behavior.
- [x] Application composition depends on package interfaces rather than implementation modules.
- [x] Capability-specific GUI code is not pulled back into the desktop shell.
- [x] Every application and shell source Python file is at most 300 physical lines.
- [x] Focused startup and desktop-shell tests pass.

## Answer

Application startup and backend lifecycle now live behind the `src.app` facade, with packaged assets,
TTS diagnostics, runtime directory preparation, CLI mode handling, and synchronous console startup
composed there. The unified Qt shell and lifecycle are application-owned and use the public settings,
profiles, importing, loot, and desktop interfaces; legacy technical GUI modules are no longer part
of the application composition.

Navigation, singleton child windows, tray and geometry persistence, startup log delivery, GUI-only
mode, backend updates, TTS connection, and close cleanup remain intact. Focused composition, shell,
importer, and profile-editor tests pass, as does the complete non-Selenium suite (688 passed, 16
skipped on macOS). The repository line hook still reports pre-existing oversized files owned by
later migration issues.
