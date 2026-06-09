______________________________________________________________________

## name: d4lf-minimal-refactor description: Improve d4lf code with the smallest reasonable structural change. Use when the user wants code simplified, brought closer to the original implementation, or cleaned up without losing newer functionality.

1. Preserve behavior first.
1. Stay close to the original implementation shape unless a larger change is clearly necessary.
1. Prefer deleting duplication or merging into existing helpers over introducing new abstractions.
1. Do not create private helper functions for one-line logic used only once; keep that logic inline.
1. Add a helper only when it is reused, carries meaningful domain language, or materially improves readability of complex logic.
1. Keep comments and naming changes minimal.
1. Do not rewrite adjacent code just for style consistency.
1. When new functionality exists, keep it while making the code path simpler and easier to review.
1. Explain what was simplified and what intentionally stayed unchanged.
