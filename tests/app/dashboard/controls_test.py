import typing
from typing import Any, cast

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src.app.dashboard.controls import ActivityLogControlsMixin


def test_select_all_checks_every_profile_and_saves_names(mocker: MockerFixture) -> None:
    first, second = mocker.Mock(), mocker.Mock()
    controls = cast("Any", ActivityLogControlsMixin())
    controls._checkboxes = {"alpha": first, "beta": second}
    controls._save_active_list = mocker.Mock()

    controls._select_all()

    first.setChecked.assert_called_once_with(True)
    second.setChecked.assert_called_once_with(True)
    controls._save_active_list.assert_called_once_with(["alpha", "beta"])


def test_config_changes_refresh_hotkey_grid_only_for_advanced_settings(mocker: MockerFixture) -> None:
    controls = cast("Any", ActivityLogControlsMixin())
    controls._setup_hotkey_grid = mocker.Mock()

    controls._on_config_changed(["general.theme"])
    controls._on_config_changed(["advanced_options.hotkey"])

    controls._setup_hotkey_grid.assert_called_once_with()
