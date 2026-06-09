______________________________________________________________________

## name: d4lf-paragon-overlay description: Handle paragon overlay changes in d4lf. Use for overlay step persistence, title card issues, click behavior, thickness/layout tweaks, restart behavior, saved state, and overlay UI regressions.

1. Read the full overlay path first, not just `paragon_overlay.py`.
1. Identify where overlay state is created, restored, persisted, and reset.
1. Check related UI callbacks, geometry/layout calculations, drawing code, and close/reopen lifecycle.
1. For display issues, confirm whether the problem is source data, truncation, font/layout, or repaint/update logic.
1. For click issues, inspect widget bindings and whether interactive elements should be disabled or visually decorative.
1. Keep overlay fixes narrow. Avoid redesigning the overlay unless explicitly requested.
1. Preserve existing overlay workflow and restart behavior outside the reported issue.
1. In the summary, state whether the fix covers startup persistence, runtime behavior, or both.
