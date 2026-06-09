---
name: d4lf-pr-review-response
description: Respond to d4lf review comments with code changes or concise technical answers. Use when a maintainer or reviewer raises issues about implementation quality, edge cases, comments, validation, or requested follow-up changes.
---

1. Restate the review point precisely.
2. Decide whether it needs a code change, an explanation, or both.
3. Keep the response technical and direct.
4. When changing code, preserve the original task scope and avoid opportunistic refactors.
5. If the reviewer asks to remove a one-use helper or unnecessary abstraction, remove it instead of defending it.
6. Avoid adding replacement helpers unless they are reused or clearly improve complex logic.
7. Mention validation only if it was actually performed.
8. For written replies, explain why the new approach is safer, smaller, or more consistent with existing code.
