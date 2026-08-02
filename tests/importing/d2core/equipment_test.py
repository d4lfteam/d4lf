from src.game_data import WEAPON_TYPES, GameCatalog, ItemType
from src.importing.d2core.catalog import CatalogStore, CatalogTransport
from src.importing.d2core.equipment import _canonical_aspect_name, _item_type, normalize_variant


def test_equipment_type_uses_safe_slot_fallbacks() -> None:
    assert _item_type("", slot="0", class_name="Druid") is ItemType.Helm
    assert _item_type("weapon", slot="5", class_name="Druid") == WEAPON_TYPES
    assert _item_type("unknown", slot="99", class_name="Druid") is None
    assert _item_type("unknown", slot="12", class_name="Druid") is ItemType.OffHandTotem


def test_aspect_catalog_matcher_preserves_catalog_entry() -> None:
    aspect_name = GameCatalog().aspect_list[0]

    assert _canonical_aspect_name({"name": aspect_name.title()}) == aspect_name


def test_unique_equipment_type_comes_from_joined_catalog_not_payload_label() -> None:
    unique_name, unique_label = next(iter(GameCatalog().aspect_unique_dict.items()))
    catalogs = CatalogStore(
        version="v1",
        transport=CatalogTransport(),
        data={
            "affix": {"affix": {}},
            "uniqueItem": {
                "uniqueItem": {"unique-key": {"key": "unique-key", "name": unique_label, "equipTypeName": "Ring"}}
            },
        },
    )
    variant = normalize_variant(
        {"gear": {"0": {"type": "uniqueItem", "key": "unique-key", "itemType": "Helm", "mods": []}}},
        variant_name="Variant 1",
        class_name="Druid",
        catalogs=catalogs,
        import_greater_affixes=False,
        require_greater_affixes=False,
        import_aspect_upgrades=False,
        warn=lambda *_args: None,
    )

    assert variant.affix_filters[0].item_type == [ItemType.Ring]
    assert variant.affix_filters[0].unique_aspect[0].name == unique_name


def test_current_d2core_catalog_schema_preserves_english_helm_stats() -> None:
    catalogs = CatalogStore(
        version="v1",
        transport=CatalogTransport(),
        data={
            "affix": {
                "affix": {
                    "S04_CoreStat_Willpower": {"key": "S04_CoreStat_Willpower", "desc": "+[100 - 121] Willpower"},
                    "S04_Life": {"key": "S04_Life", "desc": "+[1,226 - 1,450] Maximum Life"},
                    "S04_Resistance_All": {
                        "key": "S04_Resistance_All",
                        "desc": "+[327 - 392] Resistance to All Elements",
                    },
                    "S04_ResourceGain": {"key": "S04_ResourceGain", "desc": "[11.0 - 15.0]% Resource Generation"},
                    "Tempered_Generic_LifeMax_Tier3": {
                        "key": "Tempered_Generic_LifeMax_Tier3",
                        "desc": "+[1,000 - 1,500] Maximum Life",
                    },
                }
            },
            "uniqueItem": {
                "uniqueItem": {
                    "Helm_Unique_Druid_102": {
                        "key": "Helm_Unique_Druid_102",
                        "name": "Gathlen's Birthright",
                        "equipTypeName": "Helm",
                    }
                }
            },
        },
    )

    variant = normalize_variant(
        {
            "gear": {
                "0": {
                    "type": "uniqueItem",
                    "key": "Helm_Unique_Druid_102",
                    "itemType": "Helm",
                    "mods": [
                        {"name": "S04_CoreStat_Willpower"},
                        {"name": "S04_Life"},
                        {"name": "S04_Resistance_All"},
                        {"name": "S04_ResourceGain"},
                        {"name": "Tempered_Generic_LifeMax_Tier3", "greater": True},
                    ],
                }
            }
        },
        variant_name="Variant 1",
        class_name="Druid",
        catalogs=catalogs,
        import_greater_affixes=True,
        require_greater_affixes=False,
        import_aspect_upgrades=False,
        warn=lambda *_args: None,
    )

    helm = variant.affix_filters[0]
    assert [affix.name for affix in helm.affix_pool[0].count] == [
        "willpower",
        "maximum_life",
        "resistance_to_all_elements",
        "resource_generation",
        "maximum_life",
    ]
    assert [affix.want_greater for affix in helm.affix_pool[0].count] == [False, False, False, False, True]


def test_non_unique_item_keeps_safe_type_when_all_affix_joins_fail() -> None:
    catalogs = CatalogStore(version="v1", transport=CatalogTransport(), data={"affix": {"affix": {}}})
    variant = normalize_variant(
        {"gear": {"0": {"type": "rare", "itemType": "Helm", "mods": [{"name": "unknown-affix"}]}}},
        variant_name="Variant 1",
        class_name="Druid",
        catalogs=catalogs,
        import_greater_affixes=False,
        require_greater_affixes=False,
        import_aspect_upgrades=False,
        warn=lambda *_args: None,
    )

    assert variant.affix_filters[0].item_type == [ItemType.Helm]
    assert not variant.affix_filters[0].affix_pool


def test_missing_aspect_join_uses_optional_warning_code() -> None:
    catalogs = CatalogStore(
        version="v1", transport=CatalogTransport(), data={"affix": {"affix": {}}, "aspect": {"aspect": {}}}
    )
    warnings: list[tuple[str, str, str, str]] = []

    variant = normalize_variant(
        {"gear": {"0": {"type": "legendary", "itemType": "Helm", "key": "missing-aspect", "mods": []}}},
        variant_name="Variant 1",
        class_name="Druid",
        catalogs=catalogs,
        import_greater_affixes=False,
        require_greater_affixes=False,
        import_aspect_upgrades=True,
        warn=lambda *warning: warnings.append(warning),
    )

    assert variant.aspect_upgrade_filters == []
    assert warnings == [("D2C-W120", "Variant 1", "aspect", "missing-aspect")]
