# AGENTS.md - D4LF

## Project

D4LF is a Windows desktop app for filtering Diablo 4 items, sigils, and tributes from user-defined
profiles. It reads the game screen with screenshots and receives item text from a custom TTS DLL that
intercepts Diablo 4's accessibility text-to-speech pipeline.

The main UI is PyQt6. Game overlays are tkinter windows rendered above the game.

## Stack

Python 3.14 via uv; C++ for the TTS DLL in `tts/`.

## Commands

prek is used to wrap several different formaters and checkers.
Run "prek run -a" before committing to make sure all checks pass.
Don't just disable the rules, they are enabled for a reason. Fix the findings properly.
Don't change formatting changes done by the hooks, they are authorative.
Run unit tests: uv run pytest . -m "not selenium" -n logical

## Architecture

Item flow:

- TTS DLL sends named-pipe text to `src/tts.py`.
- `src/item/descr/read_descr_tts.py` parses text into `Item` objects.
- `src/item/filter.py` matches items against YAML profiles.
- Scripts show keep/junk overlays or automate mouse actions.

## Conventions

- This is a standalone tool, not a library. Do not care about any compatibility, do changes as necessary.
- Don't investigate super edge cases, especially during testing. Bring up the concern during planning stages and let the user decide.
- Runtime target is Windows. Some tests are skipped outside Windows.
- User data lives under `~/.d4lf/` including profiles, params, and logs.
- Always prefer subpackages over creating files with specific prefixes or suffixes. For example, `src.profiles.affix` and `src.profiles.aspect` are subpackages rather than
  `src.profiles_affix.py` and `src.profiles_aspect.py`.
- Put the public interface of a package in `__init__.py` and keep implementation details in submodules. For example, `src.item.filter` is the public interface for filtering items, while `src.item.filter_impl` contains the implementation.

### Python 3.14

- Don't use from __future__ imports.
- Remember deferred annotation evaluation for type annotation.
- Avoid any or object types in type annotations, use specific types instead.

### Taste

- Prefer from imports to full qualified.
- Don't prefix files, rather create a new package with the name and omit the prefix for the modules.
- In packages expose the public interface via __init__.py only.
- The unit tests should mirror the structure of the code, so a test file should correspond to a source file.
- We use pytest for testing, so don't do any importing of unittest or other testing frameworks.
- No more than 300 lines of code in Python files.

## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/` in this repository. See `docs/agents/issue-tracker.md`.

### Triage labels

Using the default triage vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` at the repository root and `docs/adr/` for ADRs. See `docs/agents/domain.md`.
