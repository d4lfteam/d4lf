---
name: d4lf-season-data-update
description: Update d4lf behavior for new Diablo 4 season data, item text, affixes, aspects, tributes, sigils, parser fixtures, or importer build data. Use when game data changes, season-specific TTS parsing fails, or profile validation rejects new game terms.
---

1. Identify whether the change belongs to generated game data, parser normalization, profile validation, tests/fixtures, or importer mappings.
2. Check the newest season-specific parser tests before changing shared parsing logic.
3. Prefer updating data files or normalization tables over hardcoding new special cases in parser code.
4. If hardcoded mappings already exist for the same source, update the existing mapping rather than adding a parallel path.
5. Keep season-specific behavior isolated unless the text format changed globally.
6. Add or update the smallest relevant fixture/test that proves the new season text is handled.
7. Run targeted parser/model tests when available.
8. In the summary, state whether the change is data-only, parser behavior, importer mapping, or validation behavior.
