import logging

from src.config.models import ProfileModel
from src.gui.importer.gui_common import save_imported_profile
from src.gui.importer.paragon_export import attach_paragon_payload


def test_save_imported_profile_saves_and_optionally_activates(mocker):
    profile = ProfileModel(name="imported profile")
    save_as_profile = mocker.patch("src.gui.importer.gui_common.save_as_profile", return_value="saved_profile")
    add_to_profiles = mocker.patch("src.gui.importer.gui_common.add_to_profiles")

    result = save_imported_profile(
        file_name="profile_name", profile=profile, url="https://example.com/build", add_to_active_profiles=True
    )

    assert result == "saved_profile"
    save_as_profile.assert_called_once_with(file_name="profile_name", profile=profile, url="https://example.com/build")
    add_to_profiles.assert_called_once_with("saved_profile")


def test_save_imported_profile_skips_activation_when_disabled(mocker):
    profile = ProfileModel(name="imported profile")
    mocker.patch("src.gui.importer.gui_common.save_as_profile", return_value="saved_profile")
    add_to_profiles = mocker.patch("src.gui.importer.gui_common.add_to_profiles")

    save_imported_profile(
        file_name="profile_name", profile=profile, url="https://example.com/build", add_to_active_profiles=False
    )

    add_to_profiles.assert_not_called()


def test_attach_paragon_payload_sets_profile_data(caplog):
    profile = ProfileModel(name="imported profile")
    paragon_steps = [[{"BoardName": "Starter Board"}]]

    with caplog.at_level(logging.INFO, logger="src.gui.importer.paragon_export"):
        attach_paragon_payload(
            profile,
            build_name="d4builds_My Build",
            source_url="https://example.com/build",
            paragon_boards_list=paragon_steps,
            missing_data_message="missing paragon data",
        )

    assert profile.Paragon is not None
    assert profile.Paragon["Name"] == "d4builds_My Build"
    assert profile.Paragon["Source"] == "https://example.com/build"
    assert profile.Paragon["ParagonBoardsList"] == paragon_steps
    assert "Paragon imported successfully" in caplog.text


def test_attach_paragon_payload_logs_when_steps_are_missing(caplog):
    profile = ProfileModel(name="imported profile")

    with caplog.at_level(logging.WARNING, logger="src.gui.importer.paragon_export"):
        attach_paragon_payload(
            profile,
            build_name="d4builds_My Build",
            source_url="https://example.com/build",
            paragon_boards_list=[],
            missing_data_message="missing paragon data",
        )

    assert profile.Paragon is None
    assert "missing paragon data" in caplog.text
