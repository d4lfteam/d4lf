from src.profiles import editor
from src.profiles.affix import DeleteAffixPool


def test_editor_public_interface() -> None:
    expected = set(editor.__all__)
    assert {"Container", "RuleListTab", "ProfileTab", "ProfileEditorWindow"} <= expected
    assert all(hasattr(editor, name) for name in expected)


def test_editor_facade_exports_profile_editor_dependencies() -> None:
    assert editor.ProfileEditorWindow.__module__ == "src.profiles.editor.window"
    assert editor.DeleteItem.__module__ == "src.profiles.editor.dialogs.delete"
    assert DeleteAffixPool.__module__ == "src.profiles.affix.dialogs"
