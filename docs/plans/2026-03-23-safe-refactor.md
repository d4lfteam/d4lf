# Safe Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Safely refactor the D4LF runtime and domain layers to reduce coupling, improve testability, and preserve current behavior.

**Architecture:** Start by adding safety nets around imports, configuration, and current behavior before extracting smaller seams from the startup path, runtime handler, filter engine, and TTS parser. Refactor by introducing new modules alongside existing code, switching one call site at a time, and keeping every step verifiable with targeted tests and small commits.

**Tech Stack:** Python 3.14, PyQt6, pytest, pydantic, yaml, keyboard/mouse hooks, Windows-specific runtime integrations

---

### Task 1: Create A Safe Baseline For Tests And Runtime Imports

**Files:**
- Modify: `src/config/helper.py`
- Modify: `src/scripts/common.py`
- Create: `tests/config/test_runtime_optional_imports.py`
- Create: `tests/scripts/test_common_imports.py`

**Step 1: Write the failing test**

```python
from importlib import reload
import sys


def test_config_helper_imports_without_keyboard(monkeypatch):
    monkeypatch.setitem(sys.modules, "keyboard", None)
    import src.config.helper as helper
    reload(helper)
    assert helper.check_greater_than_zero(1) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_runtime_optional_imports.py -v`
Expected: FAIL with `ModuleNotFoundError` or import-time failure involving `keyboard`

**Step 3: Write minimal implementation**

```python
try:
    import keyboard
except Exception:
    keyboard = None


def validate_hotkey(k: str) -> str:
    if keyboard is None:
        return k
    keyboard.parse_hotkey(k)
    return k
```

**Step 4: Add the same safety pattern to runtime-adjacent helpers**

```python
def mark_as_junk():
    if keyboard is None:
        return
    keyboard.send("space")
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/config/test_runtime_optional_imports.py tests/scripts/test_common_imports.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/config/helper.py src/scripts/common.py tests/config/test_runtime_optional_imports.py tests/scripts/test_common_imports.py
git commit -m "test: decouple optional runtime imports from unit tests"
```

### Task 2: Add Startup Smoke Tests Before Refactoring Boot Flow

**Files:**
- Create: `tests/main_test.py`
- Create: `tests/scripts/test_bootstrap_service.py`
- Modify: `src/main.py`

**Step 1: Write the failing test**

```python
def test_get_d4_local_prefs_file_returns_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    from src.main import get_d4_local_prefs_file
    assert get_d4_local_prefs_file() is None
```

**Step 2: Run test to verify it fails or exposes import/setup coupling**

Run: `pytest tests/main_test.py -v`
Expected: FAIL because importing `src.main` pulls in more runtime boot behavior than the helper needs

**Step 3: Extract a narrow bootstrap helper module**

```python
def ensure_runtime_dirs(user_dir, log_dir):
    ...


def resolve_local_prefs_file(home: Path) -> Path | None:
    ...
```

**Step 4: Point `src/main.py` at the extracted helper without changing behavior**

```python
from src.bootstrap import ensure_runtime_dirs, resolve_local_prefs_file
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/main_test.py tests/scripts/test_bootstrap_service.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/main.py src/bootstrap.py tests/main_test.py tests/scripts/test_bootstrap_service.py
git commit -m "refactor: introduce bootstrap helpers for startup flow"
```

### Task 3: Extract Script Handler Hotkey And Lifecycle Seams

**Files:**
- Create: `src/scripts/hotkeys.py`
- Create: `src/scripts/runtime_lifecycle.py`
- Modify: `src/scripts/handler.py`
- Create: `tests/scripts/test_hotkeys.py`
- Create: `tests/scripts/test_runtime_lifecycle.py`

**Step 1: Write the failing test**

```python
def test_hotkey_signature_changes_when_config_changes():
    from src.scripts.hotkeys import build_hotkey_signature
    signature = build_hotkey_signature(run_filter="f11", exit_key="f12")
    assert signature == ("f11", "f12")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/scripts/test_hotkeys.py -v`
Expected: FAIL because hotkey logic still lives only inside `ScriptHandler`

**Step 3: Extract pure helpers first**

```python
def build_hotkey_signature(...):
    return (...)


def should_refresh_hotkeys(current, previous):
    return current != previous
```

**Step 4: Extract lifecycle operations from `ScriptHandler`**

```python
class RuntimeLifecycle:
    def refresh_logging_level(self, config): ...
    def refresh_language_assets(self, config): ...
    def notify_manual_restart_required(self, reason): ...
```

**Step 5: Keep `ScriptHandler` as a thin orchestrator**

Run: `pytest tests/scripts/test_hotkeys.py tests/scripts/test_runtime_lifecycle.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/scripts/hotkeys.py src/scripts/runtime_lifecycle.py src/scripts/handler.py tests/scripts/test_hotkeys.py tests/scripts/test_runtime_lifecycle.py
git commit -m "refactor: split script handler hotkeys and lifecycle concerns"
```

### Task 4: Split Filter Matching Into Smaller Domain Functions

**Files:**
- Create: `src/item/filter_affixes.py`
- Create: `src/item/filter_uniques.py`
- Create: `src/item/filter_sigils.py`
- Create: `src/item/filter_tributes.py`
- Modify: `src/item/filter.py`
- Create: `tests/item/test_filter_affixes.py`
- Create: `tests/item/test_filter_uniques.py`
- Create: `tests/item/test_filter_sigils.py`
- Create: `tests/item/test_filter_tributes.py`

**Step 1: Write one focused failing test for a pure matcher**

```python
def test_match_affixes_returns_empty_when_min_count_not_met():
    result = match_affix_count_group(expected_affixes=[...], item_affixes=[...], min_greater_affix_count=0)
    assert result == []
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/item/test_filter_affixes.py -v`
Expected: FAIL because the matcher does not exist outside `Filter`

**Step 3: Move pure matching logic without changing public behavior**

```python
def match_affix_count_group(...): ...
def match_unique_filter(...): ...
def match_sigil_filter(...): ...
def match_tribute_filter(...): ...
```

**Step 4: Keep `Filter.should_keep()` and file-loading behavior unchanged**

```python
from src.item.filter_affixes import match_affix_count_group
```

**Step 5: Run focused and existing filter tests**

Run: `pytest tests/item/test_filter_affixes.py tests/item/test_filter_uniques.py tests/item/test_filter_sigils.py tests/item/test_filter_tributes.py tests/item/filter/filter_test.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/item/filter.py src/item/filter_affixes.py src/item/filter_uniques.py src/item/filter_sigils.py src/item/filter_tributes.py tests/item/test_filter_affixes.py tests/item/test_filter_uniques.py tests/item/test_filter_sigils.py tests/item/test_filter_tributes.py
git commit -m "refactor: split item filter matchers into dedicated modules"
```

### Task 5: Split TTS Parsing Into Parse Stages

**Files:**
- Create: `src/item/descr/parse_base_item.py`
- Create: `src/item/descr/parse_affixes.py`
- Create: `src/item/descr/parse_aspect.py`
- Modify: `src/item/descr/read_descr_tts.py`
- Create: `tests/item/test_parse_base_item.py`
- Create: `tests/item/test_parse_affixes.py`
- Create: `tests/item/test_parse_aspect.py`

**Step 1: Write the failing test**

```python
def test_create_base_item_from_tts_identifies_tribute():
    from src.item.descr.parse_base_item import create_base_item_from_tts
    item = create_base_item_from_tts(["Tribute", "Legendary Tribute of Something"])
    assert item.item_type.name == "Tribute"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/item/test_parse_base_item.py -v`
Expected: FAIL because parsing logic is still embedded in `read_descr_tts.py`

**Step 3: Extract phase modules with pure inputs and outputs**

```python
def create_base_item_from_tts(tts_item): ...
def add_affixes_from_tts(tts_section, item): ...
def parse_aspect_from_text(aspect_text, item): ...
```

**Step 4: Keep the public reader API stable**

```python
def read_item_descr(...):
    item = create_base_item_from_tts(tts_item)
    ...
```

**Step 5: Run parser regression tests**

Run: `pytest tests/item/test_parse_base_item.py tests/item/test_parse_affixes.py tests/item/test_parse_aspect.py tests/item/read_descr_season_11_tts_test.py tests/item/read_descr_season_12_tts_test.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/item/descr/read_descr_tts.py src/item/descr/parse_base_item.py src/item/descr/parse_affixes.py src/item/descr/parse_aspect.py tests/item/test_parse_base_item.py tests/item/test_parse_affixes.py tests/item/test_parse_aspect.py
git commit -m "refactor: split tts item parsing into staged modules"
```

### Task 6: Unify GUI And Console Boot Through A Shared App Runtime

**Files:**
- Create: `src/app_runtime.py`
- Modify: `src/main.py`
- Modify: `src/gui/unified_window.py`
- Create: `tests/test_app_runtime.py`

**Step 1: Write the failing test**

```python
def test_app_runtime_boot_sequence_calls_dependencies_in_order(mocker):
    from src.app_runtime import AppRuntime
    runtime = AppRuntime(...)
    runtime.start()
    assert ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_app_runtime.py -v`
Expected: FAIL because startup logic is duplicated across `main.py` and `unified_window.py`

**Step 3: Extract a shared runtime coordinator**

```python
class AppRuntime:
    def start(self):
        self.filter_loader.load()
        self.window_detector.start()
        self.script_handler.start()
        self.tts_service.start()
        self.overlay.run()
```

**Step 4: Point both boot paths at the new coordinator**

```python
runtime = AppRuntime(...)
runtime.start()
```

**Step 5: Run startup and importer-adjacent tests**

Run: `pytest tests/test_app_runtime.py tests/gui/importer -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/app_runtime.py src/main.py src/gui/unified_window.py tests/test_app_runtime.py
git commit -m "refactor: share runtime startup flow across gui and console entrypoints"
```

### Task 7: Reduce Config Model Coupling And Clarify Setting Metadata

**Files:**
- Create: `src/config/metadata.py`
- Create: `src/config/migrations.py`
- Modify: `src/config/models.py`
- Modify: `src/scripts/handler.py`
- Create: `tests/config/test_metadata.py`
- Create: `tests/config/test_migrations.py`

**Step 1: Write the failing test**

```python
def test_hotkey_metadata_is_declared_outside_model_field_definitions():
    from src.config.metadata import HOTKEY_FIELDS
    assert "advanced_options.run_filter" in HOTKEY_FIELDS
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_metadata.py -v`
Expected: FAIL because metadata is currently embedded inside model definitions

**Step 3: Extract metadata and compatibility helpers**

```python
HOTKEY_FIELDS = {...}
MANUAL_RESTART_FIELDS = {...}


def remove_deprecated_keys(parser): ...
```

**Step 4: Update consumers without changing config file format**

Run: `pytest tests/config/test_metadata.py tests/config/test_migrations.py tests/config -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/config/metadata.py src/config/migrations.py src/config/models.py src/scripts/handler.py tests/config/test_metadata.py tests/config/test_migrations.py
git commit -m "refactor: extract config metadata and migration helpers"
```

### Task 8: Add Regression-Focused Documentation And Final Smoke Checks

**Files:**
- Modify: `README.md`
- Modify: `codex.md`
- Create: `docs/refactor-regression-checklist.md`

**Step 1: Write the checklist first**

```markdown
- Launch GUI from source
- Launch console mode
- Change a hotkey and verify reload
- Load profiles and run filter tests
- Verify importer tests
```

**Step 2: Run the full practical verification set**

Run: `pytest tests/config tests/item tests/gui/importer tests/utils tests/ui -v`
Expected: PASS

**Step 3: Record any remaining manual checks**

```markdown
- TTS connection still requires Windows runtime verification
- Overlay behavior requires Diablo IV window/manual validation
```

**Step 4: Commit**

```bash
git add README.md codex.md docs/refactor-regression-checklist.md
git commit -m "docs: add safe refactor verification checklist"
```

## Risk Controls

- Do not change public config format during early refactor tasks.
- Keep `Filter.should_keep()` and current GUI entrypoints stable until extraction seams are proven by tests.
- Prefer extraction over rewrite: move code first, simplify second.
- Maintain one behavior-preserving commit per task.
- After each task, rerun only the smallest relevant test slice plus one broader regression slice.
- Treat Windows-only runtime interactions as integration boundaries; mock them in unit tests.

## Notes From Review

- `src/gui/unified_window.py` currently imports `check_for_proper_tts_configuration` from `src/main.py`, which is a coupling smell and a good extraction candidate.
- `src/config/helper.py` imports `keyboard` at import time, which currently blocks test collection when optional runtime dependencies are missing.
- `src/scripts/common.py` also performs eager runtime-dependent imports and side-effect-oriented helper logic.
- `src/item/filter.py`, `src/item/descr/read_descr_tts.py`, `src/scripts/handler.py`, and `src/paragon_overlay.py` are the highest-risk refactor targets due to size and mixed responsibilities.
- Existing tests are strongest around config, filtering, importer parsing, and utilities; startup orchestration and Windows-runtime seams need more safety coverage before deeper refactors.

## Recommended Execution Order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6
7. Task 7
8. Task 8

Plan complete and saved to `docs/plans/2026-03-23-safe-refactor.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
