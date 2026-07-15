# 07 — Complete the profile editor shell

**What to build:** Let users open, edit, save, reload, and switch profiles through one cohesive profile UI that composes the refactored rule editors without exposing their implementation.

**Blocked by:** 05 — Refactor affix, aspect, and unique profile editing; 06 — Refactor sigil, tribute, charm, and seal profile editing.

**Status:** ready-for-agent

- [ ] The profile tab and editor window use the profile package interface.
- [ ] Opening, selecting, editing, saving, reloading, and closing profiles preserve existing behavior.
- [ ] Existing tab grouping, dirty-state, and user-notification behavior remain unchanged.
- [ ] Profile-specific GUI code no longer lives in generic desktop or model buckets.
- [ ] Every touched source Python file is at most 300 physical lines.
- [ ] Focused profile-shell tests and the line guard pass.
