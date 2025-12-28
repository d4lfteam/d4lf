from src.config.models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    ComparisonType,
    ItemFilterModel,
    ProfileModel,
    SigilConditionModel,
    SigilFilterModel,
    TributeFilterModel,
    UniqueModel,
)
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity

# noinspection PyTypeChecker
affix = ProfileModel(
    name="test",
    Affixes=[
        {
            "Helm": ItemFilterModel(
                itemType=[ItemType.Helm],
                minPower=725,
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", value=5),
                            AffixFilterModel(name="cooldown_reduction", value=5),
                            AffixFilterModel(name="maximum_life", value=640),
                            AffixFilterModel(name="total_armor", value=9),
                        ]
                    )
                ],
            )
        },
        {
            "ResBoots": ItemFilterModel(
                itemType=[ItemType.Boots],
                minPower=725,
                affixPool=[
                    AffixFilterCountModel(count=[AffixFilterModel(name="movement_speed")]),
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="shadow_resistance"),
                            AffixFilterModel(name="cold_resistance"),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="poison_resistance"),
                            AffixFilterModel(name="fire_resistance"),
                        ],
                        minCount=2,
                    ),
                ],
            )
        },
        {
            "ResBootsExact": ItemFilterModel(
                itemType=[ItemType.Boots],
                minPower=725,
                affixPool=[
                    AffixFilterCountModel(count=[AffixFilterModel(name="movement_speed")]),
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="shadow_resistance", value=4, comparison=ComparisonType.smaller),
                            AffixFilterModel(name="cold_resistance", value=4, comparison=ComparisonType.smaller),
                            AffixFilterModel(name="lightning_resistance", value=4, comparison=ComparisonType.smaller),
                            AffixFilterModel(name="poison_resistance", value=4, comparison=ComparisonType.smaller),
                            AffixFilterModel(name="fire_resistance", value=4, comparison=ComparisonType.smaller),
                        ],
                        minCount=2,
                    ),
                ],
            )
        },
        {
            "GreatBoots": ItemFilterModel(
                itemType=[ItemType.Boots],
                minPower=725,
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="movement_speed"),
                            AffixFilterModel(name="cold_resistance"),
                            AffixFilterModel(name="lightning_resistance"),
                        ]
                    )
                ],
                inherentPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="maximum_evade_charges"),
                            AffixFilterModel(name="attacks_reduce_evades_cooldown_by_seconds"),
                        ],
                        minCount=1,
                    )
                ],
            )
        },
        {
            "Armor": ItemFilterModel(
                itemType=[ItemType.ChestArmor, ItemType.Legs],
                minPower=725,
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="maximum_life", value=700),
                            AffixFilterModel(name="dexterity", value=5),
                            AffixFilterModel(name="intelligence", value=5),
                            AffixFilterModel(name="dodge_chance", value=5),
                        ]
                    )
                ],
            )
        },
        {
            "Boots": ItemFilterModel(
                itemType=[ItemType.Boots],
                minPower=725,
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="movement_speed", value=10),
                            AffixFilterModel(name="maximum_life", value=700),
                            AffixFilterModel(name="cold_resistance", value=6.5),
                            AffixFilterModel(name="fire_resistance", value=5),
                            AffixFilterModel(name="poison_resistance", value=5),
                            AffixFilterModel(name="shadow_resistance", value=5),
                        ],
                        minCount=4,
                    )
                ],
            )
        },
        {"GreaterAffixes": ItemFilterModel(minGreaterAffixCount=1)},
        {
            "CountBoots": ItemFilterModel(
                itemType=[ItemType.Boots],
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", is_greater=True),
                            AffixFilterModel(name="movement_speed", is_greater=True),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="maximum_life"),
                            AffixFilterModel(name="poison_resistance"),
                            AffixFilterModel(name="shadow_resistance"),
                        ],
                        minCount=3,
                    )
                ],
                minGreaterAffixCount=2,  # Move to item level
            ),
                ],
            )
        },
    ],
)

always_keep_mythics = ProfileModel(name="keep_mythics", Uniques=[UniqueModel(minPower=900)])

aspects_filters = ProfileModel(name="aspect_profile", AspectUpgrades=["accelerating", "of_occult_dominion"])

aspect_only_unique_filters = ProfileModel(
    name="aspect_only",
    Uniques=[
        UniqueModel(aspect=AspectUniqueFilterModel(name="tibaults_will"), minPower=900),
        UniqueModel(aspect=AspectUniqueFilterModel(name="black_river"), minPower=900, profileAlias="alias_test"),
    ],
)

sigil = ProfileModel(
    name="test",
    Sigils=SigilFilterModel(
        blacklist=[SigilConditionModel(name="reduce_cooldowns_on_kill"), SigilConditionModel(name="underroot")],
        whitelist=[
            SigilConditionModel(name="jalals_vigil"),
            SigilConditionModel(name="iron_hold", condition=["shadow_damage"]),
        ],
    ),
)

sigil_blacklist_only = ProfileModel(
    name="blacklist_only", Sigils=SigilFilterModel(blacklist=[SigilConditionModel(name="iron_hold")])
)

sigil_whitelist_only = ProfileModel(
    name="whitelist_only", Sigils=SigilFilterModel(whitelist=[SigilConditionModel(name="iron_hold")])
)

sigil_priority = ProfileModel(
    name="priority",
    Sigils=SigilFilterModel(
        blacklist=[SigilConditionModel(name="reduce_cooldowns_on_kill")],
        whitelist=[SigilConditionModel(name="iron_hold", condition=["shadow_damage"])],
    ),
)

tributes = ProfileModel(
    name="tributes",
    Tributes=[
        TributeFilterModel(name="tribute_of_pride"),
        TributeFilterModel(name="mystique"),
        TributeFilterModel(rarities=[ItemRarity.Legendary, ItemRarity.Unique]),
    ],
)

unique = ProfileModel(
    name="test",
    Uniques=[
        UniqueModel(itemType=[ItemType.Scythe, ItemType.Sword], minPower=900),
        UniqueModel(itemType=[ItemType.Scythe], minPower=900),
        UniqueModel(
            affix=[
                AffixFilterModel(name="attack_speed", value=8.4),
                AffixFilterModel(name="lucky_hit_up_to_a_chance_to_restore_primary_resource", value=12),
                AffixFilterModel(name="maximum_life", value=700),
                AffixFilterModel(name="maximum_essence", value=9),
            ],
            aspect=AspectUniqueFilterModel(name="lidless_wall", value=20),
            minPower=900,
        ),
        UniqueModel(
            affix=[AffixFilterModel(name="attack_speed", value=8.4)],
            aspect=AspectUniqueFilterModel(name="soulbrand", value=20),
            minPower=900,
        ),
        UniqueModel(
            aspect=AspectUniqueFilterModel(name="soulbrand", value=15, comparison=ComparisonType.smaller), minPower=900
        ),
        UniqueModel(mythic=True),
        UniqueModel(aspect=AspectUniqueFilterModel(name="wushe_nak_pa", value=50), minPower=900),
    ],
)
