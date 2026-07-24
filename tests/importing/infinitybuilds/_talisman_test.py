from typing import TYPE_CHECKING

from src.importing.infinitybuilds._talisman import _catalog_items_by_id, _charm_set_name, _parse_talisman_gear

if TYPE_CHECKING:
    from src.importing.infinitybuilds.models import _CatalogItem


def test_talisman_payload_becomes_catalog_gear() -> None:
    gear = _parse_talisman_gear({
        "seal": "item-1128-seal",
        "charms": [None, "Talisman_Charm_Set_Barb_01_03"],
        "charmAffixes": [["unused"], ["affix-all-stats", None]],
        "charmAffixValues": [[None], [100, None]],
        "charmAffixGreater": [[None], [True, None]],
    })

    assert gear == [
        {"kind": "talisman", "slot": "seal", "itemId": "item-1128-seal"},
        {
            "kind": "talisman",
            "slot": "charm2",
            "itemId": "Talisman_Charm_Set_Barb_01_03",
            "affixes": [{"affixId": "affix-all-stats", "value": 100, "greater": True}],
        },
    ]


def test_catalog_items_can_be_found_by_infinitybuilds_source_id() -> None:
    item: _CatalogItem = {
        "id": "item-talisman-charm-set-barb-01-03-itm",
        "sourceId": "Talisman_Charm_Set_Barb_01_03.itm",
        "label": "Mlor of Sescheron's Fury",
    }

    indexed = _catalog_items_by_id([item])

    assert indexed["Talisman_Charm_Set_Barb_01_03"] is item
    assert _charm_set_name(item["label"]) == "sescherons_fury"
