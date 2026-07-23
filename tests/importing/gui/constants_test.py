from src.importing.gui.constants import INSTRUCTIONS_TEXT


def test_constants_can_be_imported():
    assert isinstance(INSTRUCTIONS_TEXT, str)
    assert len(INSTRUCTIONS_TEXT) > 0
