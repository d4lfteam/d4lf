______________________________________________________________________

## name: d4lf-ui-callback-state description: Fix d4lf UI bugs involving callbacks, widget state, persisted state, or event handling. Use for Tk/PyQt callback mismatches, remembered values not persisting, widgets being clickable when they should not be, and event-driven regressions.

1. Inspect the widget creation path, callback signature, state source, and update cycle together.
1. Verify whether the bug is caused by wrong callback arguments, stale state, incorrect defaulting, missing persistence, or duplicated update logic.
1. Keep callback signatures Ruff-safe. Avoid unused event arguments unless the framework truly requires them.
1. Reuse existing state load/save helpers where possible.
1. Avoid adding a second source of truth for the same UI state.
1. Preserve visible behavior outside the reported widget or state path.
1. In the summary, distinguish between callback fixes, persistence fixes, and rendering fixes.
