# 06 — Refactor sigil, tribute, charm, and seal profile editing

**What to build:** Preserve complete editing for sigil rules, tribute filters, charms, and seals while placing their behavior behind the profile capability interface.

Continue the public profile-editor subpackage layout established by issue 05. Shared editor
primitives belong under `src.profiles.editor`; charm/seal and sigil/tribute behavior should expose
their own cohesive subpackage facades rather than importing implementation paths across package
boundaries or using generic GUI buckets.
The public capability subpackages are `src.profiles.charm_seal`, `src.profiles.sigil`, and
`src.profiles.tribute`.

**Blocked by:** 02 — Deepen item models and filtering; 03 — Deepen profile persistence and sessions; 04 — Deepen settings and configuration.

**Status:** resolved

- [x] Sigil dungeon and affix targets remain distinct and preserve blacklist and whitelist behavior.
- [x] Tribute name and rarity remain independent OR gates, and legacy list input still migrates correctly.
- [x] Charm and seal editing preserves set-aware affixes, rarity handling, and mutual-exclusion behavior.
- [x] Create, remove, and selection dialogs remain behaviorally unchanged.
- [x] Every touched source Python file is at most 300 physical lines.
- [x] Focused editor tests and the line guard pass.

## Answer

Sigil editor state now tracks canonical dungeon and affix targets through the `src.profiles.sigil`
facade, while dialogs continue to show their display labels. Duplicate detection, removal, and
post-rejection renaming preserve blacklist and whitelist model values. Public facade coverage and
focused profile-editor tests cover the sigil, tribute, charm, and seal seams. The affected manifest
passes; the full non-Selenium suite passes 606 tests with 47 skipped tests. The repository-wide
line hook still reports the pre-existing oversized files outside this slice.
