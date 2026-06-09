---
name: d4lf-regression-scan
description: Do a focused regression scan for d4lf after a code change. Use when a fix touches UI flows, startup paths, import logic, shared helpers, or state persistence and there is a realistic risk of nearby behavior breaking.
---

1. List the nearby behaviors most likely to regress.
2. Check the changed path plus the adjacent entry/exit paths.
3. Prefer a small checklist over broad speculation.
4. If tests exist, run the most relevant ones. If not, describe manual risk areas clearly.
5. Pay special attention to startup, reopen/reload, save/restore, browser branching, and shared helper reuse.
6. End with a concise residual-risk statement.
