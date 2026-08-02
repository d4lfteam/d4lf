from src.profiles import editor
from src.profiles.affix import DeleteAffixPool
from src.profiles.editor.profile import ProfileTab
from src.profiles.ui import ProfileEditorWindow


def test_editor_public_interface() -> None:
    expected = set(editor.__all__)
    assert {"Container", "RuleListTab"} <= expected
    assert all(hasattr(editor, name) for name in expected)


def test_editor_facade_exports_profile_editor_dependencies() -> None:
    assert ProfileEditorWindow.__module__ == "src.profiles.ui.window"
    assert ProfileTab.__module__ == "src.profiles.editor.profile.tab"
    assert editor.DeleteItem.__module__ == "src.profiles.editor.dialogs.delete"
    assert DeleteAffixPool.__module__ == "src.profiles.affix.dialogs"
