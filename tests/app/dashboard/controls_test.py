import typing
from typing import cast

if typing.TYPE_CHECKING:
    from unittest.mock import Mock

    from pytest_mock import MockerFixture

    from src.app.dashboard.core import ActivityLogWidget
    from src.desktop.widgets import CheckmarkCheckBox

from src.app.dashboard.controls import ActivityLogControlsMixin


def test_select_all_checks_every_profile_and_saves_names(mocker: MockerFixture) -> None:
    first_mock: Mock = mocker.Mock()
    second_mock: Mock = mocker.Mock()
    first, second = cast("CheckmarkCheckBox", first_mock), cast("CheckmarkCheckBox", second_mock)
    controls = cast("ActivityLogWidget", ActivityLogControlsMixin())
    controls._checkboxes = {"alpha": first, "beta": second}
    save_active_list: Mock = mocker.Mock()
    controls._save_active_list = save_active_list

    controls._select_all()

    first_mock.setChecked.assert_called_once_with(True)
    second_mock.setChecked.assert_called_once_with(True)
    save_active_list.assert_called_once_with(["alpha", "beta"])


def test_config_changes_refresh_hotkey_grid_only_for_advanced_settings(mocker: MockerFixture) -> None:
    controls = cast("ActivityLogWidget", ActivityLogControlsMixin())
    setup_hotkey_grid = mocker.Mock()
    controls._setup_hotkey_grid = setup_hotkey_grid

    controls._on_config_changed(["general.theme"])
    controls._on_config_changed(["advanced_options.hotkey"])

    setup_hotkey_grid.assert_called_once_with()
