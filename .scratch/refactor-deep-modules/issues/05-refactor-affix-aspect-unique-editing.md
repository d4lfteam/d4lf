# 05 — Refactor affix, aspect, and unique profile editing

**What to build:** Preserve the complete equipment-rule editing experience while localizing affix pools, aspects, uniques, item-type selection, and their dialogs inside the profile capability.

Profile editor behavior in this slice belongs in the public `src.profiles.affix`,
`src.profiles.aspect`, `src.profiles.unique`, and `src.profiles.editor` subpackage facades. Do not
introduce implementation-module imports across package boundaries or move capability-specific widgets into a generic
GUI bucket.

**Blocked by:** 02 — Deepen item models and filtering; 03 — Deepen profile persistence and sessions; 04 — Deepen settings and configuration.

**Status:** resolved

- [x] Users can create, edit, summarize, and remove affix pools with unchanged validation and saved output.
- [x] Aspect upgrade and global unique editing preserve existing mutual-exclusion and rarity behavior.
- [x] Item type, set, rarity, minimum power, and Greater Affix Count controls preserve existing behavior.
- [x] Shared editor behavior is cohesive and private to the profile capability rather than a generic GUI bucket.
- [x] Each affected profile-editor subpackage exposes its intended behavior through `__init__.py`.
- [x] Every touched source Python file is at most 300 physical lines.
- [x] Focused profile-editor tests and the line guard pass.

## Answer

Profile editing now uses public capability subpackages: `src.profiles.affix`, `aspect`, `unique`,
`charm_seal`, `sigil`, and `tribute`. `src.profiles.editor` retains only shared editor primitives
and composition. The old generic profile-editor and dialog modules were removed; affix pools,
item controls, aspect upgrades, global uniques, and their dialogs preserve the existing model
mutations and validation behavior.

Focused editor coverage includes pool lifecycle, item-type selection, power/Greater Affix updates,
unique-aspect threshold modes, aspect upgrades, global uniques, charm/seal behavior, sigils, and
tributes. The complete non-Selenium suite passes: 604 passed and 47 skipped. All touched profile
source files are below 300 lines. The repository line hook still reports only the pre-existing
oversized files outside this slice, so its global checkbox remains open for the source-freeze work.

### Structural review correction

The final target nests affix groups under `src.profiles.affix.group` and editor dialogs and profile
composition under `src.profiles.editor.dialogs` and `.profile`. Implementations remain package-owned
with descriptive filenames; no underscore-prefixed private modules are required.
