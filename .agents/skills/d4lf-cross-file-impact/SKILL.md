______________________________________________________________________

## name: d4lf-cross-file-impact description: Analyze cross-file impact before and after a d4lf change. Use when a file interacts with shared helpers, callbacks, imports, UI flows, shared state, or packaging boundaries and there is a risk of local fixes breaking surrounding behavior.

1. Map the direct dependencies of the touched code: imports, callers, callees, shared constants, shared state, and UI entry points.
1. Look for duplicate or parallel logic in nearby files before adding new code.
1. Prefer integrating with existing flows over introducing isolated special cases.
1. When changing function signatures or return values, inspect every relevant call site.
1. When changing state, inspect load/save/default/reset paths.
1. When changing UI logic, inspect event bindings, update triggers, and lifecycle hooks.
1. Summarize cross-file impact explicitly so the user can review the risk quickly.
