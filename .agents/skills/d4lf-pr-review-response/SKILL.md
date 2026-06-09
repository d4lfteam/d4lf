______________________________________________________________________

## name: d4lf-pr-review-response description: Respond to d4lf review comments with code changes or concise technical answers. Use when a maintainer or reviewer raises issues about implementation quality, edge cases, comments, validation, or requested follow-up changes.

1. Restate the review point precisely.
1. Decide whether it needs a code change, an explanation, or both.
1. Keep the response technical and direct.
1. When changing code, preserve the original task scope and avoid opportunistic refactors.
1. If the reviewer asks to remove a one-use helper or unnecessary abstraction, remove it instead of defending it.
1. Avoid adding replacement helpers unless they are reused or clearly improve complex logic.
1. Mention validation only if it was actually performed.
1. For written replies, explain why the new approach is safer, smaller, or more consistent with existing code.
