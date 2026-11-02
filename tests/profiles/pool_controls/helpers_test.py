import pytest
from PyQt6.QtWidgets import QApplication, QWidget

from src.game_data import GameCatalog
from src.profiles import CharmFilterModel, ItemFilterModel, SealFilterModel
from src.profiles.pool_controls.helpers import affix_dict_for_widget, get_affixes_for_set, get_set_and_base_for_key


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class ConfigParent(QWidget):
    def __init__(self, config: ItemFilterModel | CharmFilterModel | SealFilterModel) -> None:
        super().__init__()
        self.config = config


def test_get_set_and_base_for_key_prefers_longest_set_prefix() -> None:
    sets = ["fury", "fury_of_the_storm"]

    assert get_set_and_base_for_key("fury_of_the_storm_damage", sets) == ("fury_of_the_storm", "damage")
    assert get_set_and_base_for_key("movement_speed", sets) == (None, "movement_speed")


def test_get_affixes_for_set_filters_and_strips_set_label() -> None:
    affix_dict = {"fury_damage": "fury Damage", "movement_speed": "Movement Speed"}

    assert get_affixes_for_set(affix_dict, ["fury"], "fury") == {"fury_damage": "Damage"}
    assert get_affixes_for_set(affix_dict, ["fury"], None) == {"movement_speed": "Movement Speed"}


@pytest.mark.parametrize(
    ("config", "dict_name"),
    [(SealFilterModel(), "seal_affix_dict"), (CharmFilterModel(), "charm_affix_dict"), (None, "affix_dict")],
)
def test_affix_dict_for_widget_follows_parent_config(qapp, mock_ini_loader, config, dict_name) -> None:
    parent = ConfigParent(config) if config is not None else None
    widget = QWidget(parent)

    assert affix_dict_for_widget(widget) is getattr(GameCatalog(), dict_name)
