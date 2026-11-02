import pytest
from PyQt6.QtWidgets import QApplication

from src.profiles import CharmFilterModel, DynamicCharmFilterModel, DynamicSealFilterModel, SealFilterModel
from src.profiles.charm_seal import CharmGroupEditor, SealGroupEditor


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_charm_and_seal_editors_namespace_auto_sync_and_aspects(qapp, mock_ini_loader, fake_settings) -> None:
    charm_editor = CharmGroupEditor(DynamicCharmFilterModel(root={"MyBuild": CharmFilterModel()}))
    seal_editor = SealGroupEditor(DynamicSealFilterModel(root={"MyBuild": SealFilterModel()}))

    charm_editor.greater_controls.auto_sync_checkbox.setChecked(True)
    seal_editor.unique_aspects.add_aspect()

    assert fake_settings == {"auto_sync_ga_charm_MyBuild": True}
    assert seal_editor.config.unique_aspect[0].name.startswith("seal_of")
