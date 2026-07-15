# 18 — Consolidate shared desktop primitives

**What to build:** Give capability UIs a small shared desktop interface for genuinely reusable widgets, dialogs, themes, activity logging, and Qt/Tk thread handling without recreating a broad GUI utility bucket.

**Blocked by:** 04 — Deepen settings and configuration; 07 — Complete the profile editor shell.

**Status:** ready-for-agent

- [ ] Only behavior with multiple real capability consumers remains in the shared desktop module.
- [ ] Shared widgets, dialogs, themes, and activity logging preserve existing appearance and interaction.
- [ ] UI-thread behavior preserves current Qt/Tk lifecycle and Windows constraints.
- [ ] Profile-, settings-, and importer-specific GUI behavior remains with its owning capability.
- [ ] Every desktop primitive source Python file is at most 300 physical lines.
- [ ] Focused widget, dialog, theme, log, and UI-thread tests pass.
