from src.profiles import editor


def test_editor_public_interface() -> None:
    expected = set(editor.__all__)
    assert {"Container", "RuleListTab", "ProfileTab", "ProfileEditorWindow"} <= expected
    assert all(hasattr(editor, name) for name in expected)
