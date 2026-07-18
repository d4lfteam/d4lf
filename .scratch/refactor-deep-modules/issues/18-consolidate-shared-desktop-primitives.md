# 18 — Consolidate shared desktop primitives

**What to build:** Give capability UIs a small shared desktop interface for genuinely reusable widgets, dialogs, themes, activity logging, and Qt/Tk thread handling without recreating a broad GUI utility bucket.

**Blocked by:** 04 — Deepen settings and configuration; 07 — Complete the profile editor shell.

**Status:** resolved

- [x] Only behavior with multiple real capability consumers remains in the shared desktop module.
- [x] Shared widgets, dialogs, themes, and activity logging preserve existing appearance and interaction.
- [x] UI-thread behavior preserves current Qt/Tk lifecycle and Windows constraints.
- [x] Profile-, settings-, and importer-specific GUI behavior remains with its owning capability.
- [x] Every desktop primitive source Python file is at most 300 physical lines.
- [x] Focused widget, dialog, theme, log, and UI-thread tests pass.

## Answer

Shared desktop behavior now has deliberate public seams: `src.desktop` owns the shared Tk thread,
while `src.desktop.widgets`, `src.desktop.activity`, and `src.desktop.themes` expose the reusable
Qt widget, activity-log, and theme primitives. Settings, importing, and the application dashboard
use those facades; profile-, settings-, and importer-specific dialogs remain with their owning
capabilities because no cross-capability dialog behavior was demonstrated.

The checkmark widget no longer imports loot behavior directly; application composition supplies the
current accent. ANSI rendering and Qt logging are shared between the dashboard and importer, and the
theme templates retain the existing dark/light selectors and runtime accent substitution. All new
desktop source files are below 300 lines, with focused tests covering widgets, rendered themes, log
delivery, and the existing Tk-thread contract.

The non-Selenium suite passes with 684 tests passed and 16 skipped on macOS. The repository-wide
line hook remains blocked by pre-existing oversized files owned by later source-migration issues.
