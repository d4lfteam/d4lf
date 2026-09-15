from src.profiles.editor.profile import ProfileEditor, ProfileTab


def test_profile_editor_interface_exposes_editor_and_tab() -> None:
    assert ProfileEditor is not None
    assert ProfileTab is not None
