from src.importing.maxroll.items import _attribute_description_corrections


def test_maxroll_item_text_correction_is_case_normalized() -> None:
    assert _attribute_description_corrections("Damage") == "damage"
