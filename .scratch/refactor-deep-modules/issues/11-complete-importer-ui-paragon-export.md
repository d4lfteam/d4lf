# 11 — Complete importer UI and Paragon export

**What to build:** Let users select a source and variant, preview or customize the profile filename, import the build, and store its profile and optional Paragon payload through one importing interface.

**Blocked by:** 09 — Migrate D4Builds and Maxroll adapters; 10 — Migrate InfinityBuilds and Mobalytics adapters.

**Status:** complete

- [x] Importer window behavior is unchanged for every supported source.
- [x] Generated and custom profile filenames preserve their selected-part behavior and ordering.
- [x] Successful imports persist equivalent profile and optional Paragon payload data.
- [x] Errors, retries, cancellation, and user notifications remain explicit and behaviorally unchanged.
- [x] Importer-specific GUI code lives with the importing capability.
- [x] Every touched source Python file is at most 300 physical lines, and focused tests pass.
