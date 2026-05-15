from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    GlobalUniqueModel,
    ItemFilterModel,
    ProfileModel,
    SigilConditionModel,
    SigilFilterModel,
    TributeFilterModel,
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
                            AffixFilterModel(name="shadow_resistance", value=4),
                            AffixFilterModel(name="cold_resistance", value=4),
                            AffixFilterModel(name="lightning_resistance", value=4),
                            AffixFilterModel(name="poison_resistance", value=4),
                            AffixFilterModel(name="fire_resistance", value=4),
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
        {
            "PercentBoots": ItemFilterModel(
                itemType=[ItemType.Boots],
                minPower=725,
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="movement_speed", minPercentOfAffix=80),
                            AffixFilterModel(name="dodge_chance"),
                        ]
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
                            AffixFilterModel(name="intelligence", want_greater=True),
                            AffixFilterModel(name="movement_speed", want_greater=True),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="maximum_life"),
                            AffixFilterModel(name="poison_resistance"),
                            AffixFilterModel(name="shadow_resistance"),
                        ],
                        minCount=3,
                    )
                ],
                minGreaterAffixCount=2,
            )
        },
        {
            "CountBootsMatch": ItemFilterModel(
                itemType=[ItemType.Boots],
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", want_greater=True),
                            AffixFilterModel(name="movement_speed", want_greater=True),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="maximum_life"),
                        ],
                        minCount=3,
                    )
                ],
                minGreaterAffixCount=1,  # Should match - only needs 1 greater, has 2
            )
        },
        {
            "CountBootsNoMatch": ItemFilterModel(
                itemType=[ItemType.Boots],
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", want_greater=True),
                            AffixFilterModel(name="movement_speed", want_greater=True),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="maximum_life"),
                        ],
                        minCount=3,
                    )
                ],
                minGreaterAffixCount=3,  # Should NOT match - needs 3 greater, only has 2
            )
        },
    ],
)

always_keep_mythics = ProfileModel(name="keep_mythics", GlobalUniques=[GlobalUniqueModel(minPower=900)])

aspects_filters = ProfileModel(name="aspect_profile", AspectUpgrades=["accelerating", "aggressive"])

global_unique = ProfileModel(
    name="test",
    GlobalUniques=[
        GlobalUniqueModel(minPower=900),
        GlobalUniqueModel(minGreaterAffixCount=2),
        GlobalUniqueModel(minPercentOfAspect=80, profileAlias="good_stuff"),
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

# noinspection PyTypeChecker
unique_affixes = ProfileModel(
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
                        ],
                        minCount=1,
                    )
                ],
                # Due to quirks of pydantic this has to be passed in as a map and not the object
                uniqueAspect={"name": "crown_of_lucion", "value": 12},
            )
        },
        {
            "PercentBoots": ItemFilterModel(
                itemType=[ItemType.Boots],
                minPower=725,
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="movement_speed", minPercentOfAffix=80),
                            AffixFilterModel(name="dodge_chance"),
                        ]
                    )
                ],
                uniqueAspect={"name": "penitent_greaves", "minPercentOfAspect": 50},
            )
        },
        {
            "CountBoots": ItemFilterModel(
                itemType=[ItemType.Boots],
                affixPool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", want_greater=True),
                            AffixFilterModel(name="movement_speed", want_greater=True),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="maximum_life"),
                            AffixFilterModel(name="poison_resistance"),
                            AffixFilterModel(name="shadow_resistance"),
                        ],
                        minCount=3,
                    )
                ],
                uniqueAspect={"name": "flickerstep"},
                minGreaterAffixCount=2,
            )
        },
        {"UniqueAspectOnly": ItemFilterModel(uniqueAspect={"name": "battle_trance"})},
        {
            "SmallerUniqueAspectValue": ItemFilterModel(
                itemType=[ItemType.Shield], uniqueAspect={"name": "crown_of_lucion", "value": 12}
            )
        },
        {"UniqueAspectWithGA": ItemFilterModel(uniqueAspect={"name": "flickerstep"}, minGreaterAffixCount=2)},
    ],
)

tributes = ProfileModel(
    name="tributes",
    Tributes=[
        TributeFilterModel(name="tribute_of_andariel"),
        TributeFilterModel(name="harmony"),
        TributeFilterModel(rarities=[ItemRarity.Legendary, ItemRarity.Unique]),
    ],
)
