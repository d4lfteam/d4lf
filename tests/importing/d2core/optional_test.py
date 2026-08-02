from src.game_data import GameCatalog
from src.importing.d2core.catalog import CatalogStore, CatalogTransport
from src.importing.d2core.optional import normalize_talismans


def test_disabled_talisman_category_is_silent() -> None:
    affix_key = next(iter(GameCatalog().charm_affix_dict))
    catalogs = CatalogStore(
        version="v1",
        transport=CatalogTransport(),
        data={
            "talisman": {
                "charm": {"charm-key": {"key": "charm-key", "name": "Charm"}},
                "seal": {"seal-key": {"key": "seal-key", "name": "Seal"}},
                "itemSets": {},
                "affixes": {
                    "charm": {affix_key: {"key": affix_key, "desc": GameCatalog().charm_affix_dict[affix_key]}},
                    "seal": {},
                },
            }
        },
    )
    warnings: list[tuple[str, str, str, str]] = []

    def warn(code: str, variant: str, module: str, key: str) -> None:
        warnings.append((code, variant, module, key))

    charms, seals = normalize_talismans(
        {
            "charms": [
                {"type": "Charm", "key": "charm-key", "mods": [{"name": affix_key}]},
                {"type": "HoradricSeal", "key": "seal-key", "mods": []},
            ]
        },
        variant_name="Variant 1",
        catalogs=catalogs,
        import_greater_affixes=False,
        require_greater_affixes=False,
        import_charms=True,
        import_seals=False,
        warn=warn,
    )

    assert len(charms) == 1
    assert not seals
    assert not warnings


def test_charm_set_and_unique_claim_is_rejected_even_when_set_join_is_missing() -> None:
    catalogs = CatalogStore(
        version="v1",
        transport=CatalogTransport(),
        data={
            "talisman": {
                "charm": {"charm-key": {"key": "charm-key", "name": "Charm", "set": "missing-set"}},
                "seal": {},
                "itemSets": {},
                "affixes": {"charm": {}, "seal": {}},
            }
        },
    )
    warnings: list[tuple[str, str, str, str]] = []

    charms, seals = normalize_talismans(
        {"charms": [{"type": "Charm", "key": "charm-key", "itemQuality": "Unique"}]},
        variant_name="Variant 1",
        catalogs=catalogs,
        import_greater_affixes=False,
        require_greater_affixes=False,
        import_charms=True,
        import_seals=True,
        warn=lambda *warning: warnings.append(warning),
    )

    assert not charms
    assert not seals
    assert warnings == [("D2C-W120", "Variant 1", "charm", "charm-key")]
