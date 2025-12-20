from src.item.data.affix import Affix
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.models import Item


class TestSigil(Item):
    def __init__(self, rarity=ItemRarity.Common, item_type=ItemType.Sigil, **kwargs):
        super().__init__(rarity=rarity, item_type=item_type, **kwargs)


sigils = [
    (
        "affix in blacklist",
        [],
        TestSigil(affixes=[Affix(name="death_pulse"), Affix(name="reduce_cooldowns_on_kill", value=0.25)]),
    ),
    ("inherent in blacklist", [], TestSigil(inherent=[Affix(name="underroot")])),
    ("affix not in whitelist", [], TestSigil(inherent=[Affix(name="lubans_rest")])),
    ("condition not met", [], TestSigil(inherent=[Affix(name="iron_hold")])),
    (
        "ok_1",
        ["test"],
        TestSigil(
            affixes=[
                Affix(name="extra_shrines"),
                Affix(name="empowered_elites_shock_lance"),
                Affix(name="monster_burning_damage", value=30.0),
                Affix(name="monster_regen", value=1.5),
                Affix(name="slowing_projectiles", value=50.0),
            ],
            inherent=[Affix(name="jalals_vigil")],
        ),
    ),
    (
        "ok_2",
        ["test"],
        TestSigil(
            affixes=[
                Affix(name="increased_healing", value=15.0),
                Affix(name="volcanic"),
                Affix(name="monster_cold_damage", value=20.0),
                Affix(name="monster_poison_resist", value=60),
                Affix(name="armor_breakers", value=7.0),
            ],
            inherent=[Affix(name="jalals_vigil")],
        ),
    ),
    (
        "ok_3",
        ["test"],
        TestSigil(
            affixes=[
                Affix(name="quick_killer", value=2.0),
                Affix(name="nightmare_portal"),
                Affix(name="monster_attack_speed", value=25.0),
                Affix(name="monster_burning_resist", value=60.0),
                Affix(name="backstabbers"),
            ],
            inherent=[Affix(name="jalals_vigil")],
        ),
    ),
    (
        "ok_4",
        ["test"],
        TestSigil(
            affixes=[
                Affix(name="shadow_damage", value=2.0),
                Affix(name="nightmare_portal"),
                Affix(name="monster_attack_speed", value=25.0),
                Affix(name="monster_burning_resist", value=60.0),
                Affix(name="backstabbers"),
            ],
            inherent=[Affix(name="iron_hold")],
        ),
    ),
]

sigil_jalal = TestSigil(inherent=[Affix(name="jalals_vigil")])

sigil_priority = TestSigil(
    affixes=[Affix(name="shadow_damage", value=2.0), Affix(name="reduce_cooldowns_on_kill")],
    inherent=[Affix(name="iron_hold")],
)
