from src.settings.models import AdvancedOptionsModel, GeneralModel, UiRoiModel


def test_models_interface_exposes_settings_models() -> None:
    assert AdvancedOptionsModel is not None
    assert GeneralModel is not None
    assert UiRoiModel is not None
