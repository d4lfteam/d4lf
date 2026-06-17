# Fix sigil editor: global top-level affix blacklist (#502)

Status: complete

## Parent

`.scratch/rarity-filter/PRD.md`

## What to build

Fix the sigil profile editor so a user can blacklist top-level sigil affixes globally, without first picking a dungeon (#502). The current editor is dungeon-first and cannot express "blacklist this affix on every sigil."

This slice is HITL: the fix approach is settled in ADR-0003 — the sigil tab derives a `kind` (`affix`/`dungeon`) from the rule name; affix-kind rows are global and hide the condition UI; dungeon+condition rows are unchanged. It is a prerequisite for adding the sigil rarity control to the GUI (slice 04).

## Acceptance criteria

- [x] Fix approach for #502 agreed with maintainer before implementation. (ADR-0003: kind derived from name; affix-kind hides condition UI; loose name validation)
- [x] A user can add a global affix to the sigil blacklist without selecting a dungeon. (kind=affix/dungeon split in `CreateSigil`/`SigilWidget`)
- [x] Affix-kind rows render only the affix picker — condition list/buttons hidden. (`SigilWidget.setup_ui`; `test_affix_kind_has_no_condition_list`)
- [x] Existing dungeon+condition sigil rules continue to load and edit correctly. (`derive_sigil_kind` on load; `test_sigils_tab.py`)
- [x] Profiles produced by the fixed editor validate against `SigilFilterModel`.
- [x] Manually verified in the profile editor.

## Blocked by

- None - design signed off (ADR-0003); only manual GUI verify remains
