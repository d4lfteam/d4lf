import subprocess
import sys
from pathlib import Path

from src.profiles.ui import ProfileEditorWindow


def test_ui_facade_exports_profile_editor_window() -> None:
    assert ProfileEditorWindow.__module__ == "src.profiles.ui.window"


def test_ui_facade_imports_in_a_fresh_process() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "from src.profiles.ui import ProfileEditorWindow"],
        cwd=Path(__file__).parents[3],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
