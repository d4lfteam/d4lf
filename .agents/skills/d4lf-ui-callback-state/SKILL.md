---
name: d4lf-ui-callback-state
description: Fix d4lf UI bugs involving callbacks, widget state, persisted state, or event handling. Use for Tk/PyQt callback mismatches, remembered values not persisting, widgets being clickable when they should not be, and event-driven regressions.
---

1. Inspect the widget creation path, callback signature, state source, and update cycle together.
2. Verify whether the bug is caused by wrong callback arguments, stale state, incorrect defaulting, missing persistence, or duplicated update logic.
3. Keep callback signatures Ruff-safe. Avoid unused event arguments unless the framework truly requires them.
4. Reuse existing state load/save helpers where possible.
5. Avoid adding a second source of truth for the same UI state.
6. Preserve visible behavior outside the reported widget or state path.
7. In the summary, distinguish between callback fixes, persistence fixes, and rendering fixes.
