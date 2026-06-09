______________________________________________________________________

## name: d4lf-tts-startup description: Diagnose d4lf startup, TTS DLL, named pipe, Windows permission, Diablo process detection, screen reader, or runtime environment problems. Use when the app starts but receives no item data, the DLL install path is suspect, startup validation fails, or Windows-only dependencies behave differently locally and in CI.

1. Separate startup failures from runtime no-data failures: process launch, config load, DLL install, named pipe listener, Diablo accessibility/TTS output, and overlay display are different paths.
1. Inspect `src/main.py`, `src/tts.py`, startup validation, process/window helpers, and the relevant script handler path together.
1. Check whether the issue depends on Windows APIs, admin permissions, game process state, or user data under `~/.d4lf/`.
1. Preserve existing Windows-only behavior; do not add cross-platform fallbacks unless explicitly requested.
1. Avoid broad retries or silent exception swallowing around named pipes or process detection.
1. Prefer clear startup messages or logging when the failure is environmental.
1. In the summary, state which startup stage was checked and what remains environment-dependent.
