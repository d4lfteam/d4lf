---
name: d4lf-log-triage
description: Triage d4lf errors from stack traces, terminal logs, or user-reported runtime output. Use when the user pastes exceptions, warnings, duplicate messages, startup output, or strange runtime behavior and wants a precise code fix or diagnosis.
---

1. Extract the concrete failing frame, module, and symptom from the log.
2. Distinguish root cause from secondary traceback noise.
3. Trace the error into the relevant code path and connected files.
4. If the log suggests repeated output, determine whether it comes from repeated calls, duplicated bindings, repeated initialization, or multiple windows/threads.
5. Prefer code-level explanation tied to the pasted output.
6. When certainty is limited, say which assumption is strongest and what evidence supports it.
