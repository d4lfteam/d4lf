from src.profiles.editor.profile import PROFILE_TABNAME, ProfileEditor, ProfileTab


def test_profile_editor_interface_exposes_editor_and_tab() -> None:
    assert PROFILE_TABNAME
    assert ProfileEditor is not None
    assert ProfileTab is not None
