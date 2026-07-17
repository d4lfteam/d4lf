# 07 — Complete the profile editor shell

**What to build:** Let users open, edit, save, reload, and switch profiles through one cohesive profile UI that composes the refactored rule editors without exposing their implementation.

The shell composes the public profile editor subpackage facades (`src.profiles.affix`,
`src.profiles.aspect`, `src.profiles.unique`, `src.profiles.charm_seal`, `src.profiles.sigil`, and
`src.profiles.tribute`); it must not reach into implementation modules.

**Blocked by:** 05 — Refactor affix, aspect, and unique profile editing; 06 — Refactor sigil, tribute, charm, and seal profile editing.

**Status:** resolved

- [x] The profile tab and editor window use the profile package interface.
- [x] Opening, selecting, editing, saving, reloading, and closing profiles preserve existing behavior.
- [x] Existing tab grouping, dirty-state, and user-notification behavior remain unchanged.
- [x] Profile-specific GUI code no longer lives in generic desktop or model buckets.
- [x] Every touched source Python file is at most 300 physical lines.
- [ ] Focused profile-shell tests and the line guard pass.

## Answer

The profile editor shell now exposes its Qt last-opened store through the editor facade, composes
the public profile and item interfaces, supports an explicit initial profile without duplicate
loading, and preserves the current editor when switching or reloading fails. Deferred window
construction is safe across an early close. Focused shell/profile-editor tests pass, as does the
full non-Selenium suite (614 passed, 47 skipped), and every touched Python file is within 300 lines.
The repository-wide line hook remains blocked by pre-existing oversized files outside this slice.
