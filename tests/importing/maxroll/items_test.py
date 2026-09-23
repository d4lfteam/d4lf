import logging

from src.game_data import ItemType
from src.importing.maxroll.items import _attribute_description_corrections, _find_item_affixes


def test_maxroll_item_text_correction_is_case_normalized() -> None:
    assert _attribute_description_corrections("Damage") == "damage"


def test_find_item_affixes_skips_set_count_attribute_at_info_level(caplog) -> None:
    mapping_data = {
        "affixes": {
            "HellfireTorch_Necro_05": {
                "id": 1,
                "magicType": 3,
                "attributes": [{"id": 828, "param": 2297198}],
                "desc": "+1 Set count to Rathma's Waking Touch.",
            }
        },
        "attributes": {"828": {"name": "Set_Item_Count"}},
        "skills": {},
    }

    with caplog.at_level(logging.INFO, logger="src.importing.maxroll.items"):
        affixes = _find_item_affixes(mapping_data=mapping_data, item_affixes=[{"nid": 1}], item_type=ItemType.Amulet)

    assert affixes == []
    assert any(record.levelno == logging.INFO and "Set_Item_Count" in record.message for record in caplog.records)
    assert not any(record.levelno >= logging.WARNING for record in caplog.records)
