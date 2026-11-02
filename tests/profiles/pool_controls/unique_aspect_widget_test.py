import pytest
from PyQt6.QtWidgets import QApplication

from src.game_data import GameCatalog
from src.profiles import AspectUniqueFilterModel
from src.profiles.pool_controls import UniqueAspectWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_unique_aspect_widget_value_and_percent_are_mutually_exclusive(qapp, mock_ini_loader) -> None:
    aspect_name = next(iter(GameCatalog().aspect_unique_dict))
    model = AspectUniqueFilterModel(name=aspect_name, value=1.5)
    widget = UniqueAspectWidget(model)

    widget.mode_combo.setCurrentText("Min %")
    widget.value_edit.setText("25")
    assert model.min_percent_of_aspect == 25
    assert model.value is None

    widget.mode_combo.setCurrentText("Value")
    widget.value_edit.setText("2.5")
    assert model.value == pytest.approx(2.5)
    assert model.min_percent_of_aspect == 0
