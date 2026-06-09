---
name: d4lf-trace-bugfix
description: Trace a d4lf bug end to end before editing code. Use for bug reports, regressions, odd UI behavior, state loss, import problems, callback issues, or cross-file failures. Do not use for simple one-line text changes.
---

1. Restate the reported symptom in one sentence.
2. Identify the probable execution path before changing code.
3. Read the target file and the connected callers, callees, helpers, imports, callbacks, shared state, and UI flow.
4. Prefer tracing the actual data flow over guessing from one file in isolation.
5. Write down the likely root cause in concrete terms: wrong state source, wrong callback path, stale value, import path issue, duplicated logic, ordering issue, or side effect.
6. Apply the smallest fix that addresses that root cause.
7. Preserve existing behavior unless the task explicitly asks for behavior changes.
8. Avoid parallel replacement logic when an existing function or helper can be extended safely.
9. After the change, re-check the same execution path for obvious regressions.
10. In the final summary, report: symptom, root cause, files touched, cross-file impact, and what was or was not verified.
