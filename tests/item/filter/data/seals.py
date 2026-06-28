from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.models import Item

seals = [
    (
        "legendary seal affix and rarity match",
        ["seal_charm.Seals.resistance"],
        Item(
            item_type=ItemType.HoradricSeal,
            name="resistant_horadric_seal_of_glory",
            original_name="RESISTANT HORADRIC SEAL OF GLORY",
            rarity=ItemRarity.Legendary,
            affixes=[
                Affix(name="resistance_to_all_elements", value=7.5, min_value=7.5, max_value=10.0),
                Affix(name="sescherons_fury_damage_reduction", value=8.0, min_value=7.0, max_value=11.0),
                Affix(name="charm_slot", value=1.0),
            ],
        ),
    ),
    (
        "legendary seal greater affix count match",
        ["seal_charm.Seals.greater_cains", "seal_charm.Seals.resistance"],
        Item(
            item_type=ItemType.HoradricSeal,
            name="resistant_horadric_seal_of_current",
            original_name="RESISTANT HORADRIC SEAL OF CURRENT",
            rarity=ItemRarity.Legendary,
            affixes=[
                Affix(name="resistance_to_all_elements", value=8.5, min_value=7.5, max_value=10.0),
                Affix(
                    name="cains_wild_lightning_mana_per_second",
                    value=3.0,
                    min_value=3.0,
                    max_value=4.0,
                    type=AffixType.greater,
                ),
                Affix(name="tal_rashas_threefold_way_to_ball_lightning", value=3.0, min_value=2.0, max_value=3.0),
            ],
        ),
    ),
    (
        "mythic always kept",
        ["Mythic Seal"],
        Item(
            item_type=ItemType.HoradricSeal,
            name="resistant_horadric_seal_of_glory",
            rarity=ItemRarity.Mythic,
            affixes=[Affix(name="resistance_to_all_elements", type=AffixType.greater)],
        ),
    ),
]
