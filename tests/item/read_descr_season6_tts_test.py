import pytest

import src.tts
from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr_tts import read_descr
from src.item.models import Item

items = [
    (
        [
            "BLOOD ARTISANS CUIRASS",
            "Unique Chest Armor",
            "750 Item Power",
            "210 Armor",
            "+305 Maximum Life [305 - 340]",
            "+125.0% Damage for 4 Seconds After Picking Up a Blood Orb [98.0 - 125.0]%[4]",
            "Blood Orbs Restore +9 Essence [8 - 12]",
            "+3 to Bone Spirit [2 - 3]",
            "When you pick up 5 [10 - 3] Blood Orbs, a free Bone Spirit is spawned, dealing bonus damage based on your current Life percent.",
            "Empty Socket",
            "The infamous Necromancer Gaza-Thuls mastery over blood magic was indisputable. Many suspect that upon his death, his skin was used to fashion this eldritch armor.. - Barretts Book of Implements",
            "Requires Level 60Necromancer. Only. Unique Equipped",
            "Sell Value: 184,341 Gold",
            "Durability: 100/100",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=340.0,
                    min_value=305.0,
                    name="maximum_life",
                    text="+305 Maximum Life [305 - 340]",
                    type=AffixType.normal,
                    value=305.0,
                ),
                Affix(
                    max_value=125.0,
                    min_value=98.0,
                    name="damage_for_seconds_after_picking_up_a_blood_orb",
                    text="+125.0% Damage for 4 Seconds After Picking Up a Blood Orb [98.0 - 125.0]%[4]",
                    type=AffixType.normal,
                    value=125.0,
                ),
                Affix(
                    max_value=12.0,
                    min_value=8.0,
                    name="blood_orbs_restore_essence",
                    text="Blood Orbs Restore +9 Essence [8 - 12]",
                    type=AffixType.normal,
                    value=9.0,
                ),
                Affix(
                    max_value=3.0,
                    min_value=2.0,
                    name="to_bone_spirit",
                    text="+3 to Bone Spirit [2 - 3]",
                    type=AffixType.normal,
                    value=3.0,
                ),
            ],
            aspect=Aspect(
                name="blood_artisans_cuirass",
                text="When you pick up 5 [10 - 3] Blood Orbs, a free Bone Spirit is spawned, dealing bonus damage based on your current Life percent.",
                value=5.0,
            ),
            codex_upgrade=False,
            inherent=[],
            item_type=ItemType.ChestArmor,
            name="blood_artisans_cuirass",
            power=750,
            rarity=ItemRarity.Unique,
        ),
    ),
    # Ensuring mythics are read correctly
    (
        [
            "HARLEQUIN CREST",
            "Ancestral Mythic Unique Helm",
            "800 Item Power",
            "Masterwork: 12 / 12",
            "128 Armor",
            "+1,760 Maximum Life [1,760]",
            "+26 Maximum Resource [26]",
            "+682 Armor",
            "29.0% Cooldown Reduction [29.0]%",
            "Gain 20% Damage Reduction. In addition, gain +4 Ranks to all Skills.",
            "+60 Intelligence",
            "+40 Intelligence",
            "This headdress was once worn by an assassin disguised as a court mage. Her treachery was unveiled, but not before she used its magic to curse the kings entire lineage.. - The Fall of House Aston",
            "Requires Level 35. Account Bound. Unique Equipped",
            "Sell Value: 164,263 Gold",
            "Durability: 100/100",
            "Right mouse button",
        ],
        Item(
            affixes=[
                Affix(
                    max_value=1760.0,
                    min_value=1760.0,
                    name="maximum_life",
                    text="+1,760 Maximum Life [1,760]",
                    type=AffixType.normal,
                    value=1760.0,
                ),
                Affix(
                    max_value=26.0,
                    min_value=26.0,
                    name="maximum_resource",
                    text="+26 Maximum Resource [26]",
                    type=AffixType.normal,
                    value=26.0,
                ),
                Affix(
                    max_value=None, min_value=None, name="armor", text="+682 Armor", type=AffixType.greater, value=682.0
                ),
                Affix(
                    max_value=29.0,
                    min_value=29.0,
                    name="cooldown_reduction",
                    text="29.0% Cooldown Reduction [29.0]%",
                    type=AffixType.normal,
                    value=29.0,
                ),
            ],
            aspect=Aspect(
                name="harlequin_crest",
                text="Gain 20% Damage Reduction. In addition, gain +4 Ranks to all Skills.",
                value=20.0,
            ),
            codex_upgrade=False,
            cosmetic_upgrade=False,
            inherent=[],
            item_type=ItemType.Helm,
            name="harlequin_crest",
            power=800,
            rarity=ItemRarity.Mythic,
        ),
    ),
]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_items(input_item: list[str], expected_item: Item):
    src.tts.LAST_ITEM = input_item
    item = read_descr()
    assert item == expected_item
