from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
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
    affixes=[
        {
            "Helm": ItemFilterModel(
                item_type=[ItemType.Helm],
                min_power=725,
                affix_pool=[
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
                item_type=[ItemType.Boots],
                min_power=725,
                affix_pool=[
                    AffixFilterCountModel(count=[AffixFilterModel(name="movement_speed")]),
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="shadow_resistance"),
                            AffixFilterModel(name="cold_resistance"),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="poison_resistance"),
                            AffixFilterModel(name="fire_resistance"),
                        ],
                        min_count=2,
                    ),
                ],
            )
        },
        {
            "ResBootsExact": ItemFilterModel(
                item_type=[ItemType.Boots],
                min_power=725,
                affix_pool=[
                    AffixFilterCountModel(count=[AffixFilterModel(name="movement_speed")]),
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="shadow_resistance", value=4),
                            AffixFilterModel(name="cold_resistance", value=4),
                            AffixFilterModel(name="lightning_resistance", value=4),
                            AffixFilterModel(name="poison_resistance", value=4),
                            AffixFilterModel(name="fire_resistance", value=4),
                        ],
                        min_count=2,
                    ),
                ],
            )
        },
        {
            "GreatBoots": ItemFilterModel(
                item_type=[ItemType.Boots],
                min_power=725,
                affix_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="movement_speed"),
                            AffixFilterModel(name="cold_resistance"),
                            AffixFilterModel(name="lightning_resistance"),
                        ]
                    )
                ],
                inherent_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="maximum_evade_charges"),
                            AffixFilterModel(name="attacks_reduce_evades_cooldown_by_seconds"),
                        ],
                        min_count=1,
                    )
                ],
            )
        },
        {
            "Armor": ItemFilterModel(
                item_type=[ItemType.ChestArmor, ItemType.Legs],
                min_power=725,
                affix_pool=[
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
                item_type=[ItemType.Boots],
                min_power=725,
                affix_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="movement_speed", value=10),
                            AffixFilterModel(name="maximum_life", value=700),
                            AffixFilterModel(name="cold_resistance", value=6.5),
                            AffixFilterModel(name="fire_resistance", value=5),
                            AffixFilterModel(name="poison_resistance", value=5),
                            AffixFilterModel(name="shadow_resistance", value=5),
                        ],
                        min_count=4,
                    )
                ],
            )
        },
        {
            "PercentBoots": ItemFilterModel(
                item_type=[ItemType.Boots],
                min_power=725,
                affix_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="movement_speed", min_percent_of_affix=80),
                            AffixFilterModel(name="dodge_chance"),
                        ]
                    )
                ],
            )
        },
        {"GreaterAffixes": ItemFilterModel(min_greater_affix_count=1)},
        {
            "CountBoots": ItemFilterModel(
                item_type=[ItemType.Boots],
                affix_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", want_greater=True),
                            AffixFilterModel(name="movement_speed", want_greater=True),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="maximum_life"),
                            AffixFilterModel(name="poison_resistance"),
                            AffixFilterModel(name="shadow_resistance"),
                        ],
                        min_count=3,
                    )
                ],
                min_greater_affix_count=2,
            )
        },
        {
            "CountBootsMatch": ItemFilterModel(
                item_type=[ItemType.Boots],
                affix_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", want_greater=True),
                            AffixFilterModel(name="movement_speed", want_greater=True),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="maximum_life"),
                        ],
                        min_count=3,
                    )
                ],
                min_greater_affix_count=1,  # Should match - only needs 1 greater, has 2
            )
        },
        {
            "CountBootsNoMatch": ItemFilterModel(
                item_type=[ItemType.Boots],
                affix_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", want_greater=True),
                            AffixFilterModel(name="movement_speed", want_greater=True),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="maximum_life"),
                        ],
                        min_count=3,
                    )
                ],
                min_greater_affix_count=3,  # Should NOT match - needs 3 greater, only has 2
            )
        },
    ],
)

always_keep_mythics = ProfileModel(name="keep_mythics", global_uniques=[GlobalUniqueModel(min_power=900)])

aspects_filters = ProfileModel(name="aspect_profile", aspect_upgrades=["accelerating", "aggressive"])

global_unique = ProfileModel(
    name="test",
    global_uniques=[
        GlobalUniqueModel(min_power=900),
        GlobalUniqueModel(min_greater_affix_count=2),
        GlobalUniqueModel(min_percent_of_aspect=80, profile_alias="good_stuff"),
    ],
)

sigil = ProfileModel(
    name="test",
    sigils=SigilFilterModel(
        blacklist=[SigilConditionModel(name="reduce_cooldowns_on_kill"), SigilConditionModel(name="underroot")],
        whitelist=[
            SigilConditionModel(name="jalals_vigil"),
            SigilConditionModel(name="iron_hold", condition=["shadow_damage"]),
        ],
    ),
)

sigil_blacklist_only = ProfileModel(
    name="blacklist_only", sigils=SigilFilterModel(blacklist=[SigilConditionModel(name="iron_hold")])
)

sigil_whitelist_only = ProfileModel(
    name="whitelist_only", sigils=SigilFilterModel(whitelist=[SigilConditionModel(name="iron_hold")])
)

sigil_priority = ProfileModel(
    name="priority",
    sigils=SigilFilterModel(
        blacklist=[SigilConditionModel(name="reduce_cooldowns_on_kill")],
        whitelist=[SigilConditionModel(name="iron_hold", condition=["shadow_damage"])],
    ),
)

# noinspection PyTypeChecker
unique_affixes = ProfileModel(
    name="test",
    affixes=[
        {
            "Helm": ItemFilterModel(
                item_type=[ItemType.Helm],
                min_power=725,
                affix_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", value=5),
                            AffixFilterModel(name="cooldown_reduction", value=5),
                            AffixFilterModel(name="maximum_life", value=640),
                            AffixFilterModel(name="total_armor", value=9),
                        ],
                        min_count=1,
                    )
                ],
                # Due to quirks of pydantic this has to be passed in as a map and not the object
                unique_aspect={"name": "crown_of_lucion", "value": 12},
            )
        },
        {
            "PercentBoots": ItemFilterModel(
                item_type=[ItemType.Boots],
                min_power=725,
                affix_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="movement_speed", min_percent_of_affix=80),
                            AffixFilterModel(name="dodge_chance"),
                        ]
                    )
                ],
                unique_aspect={"name": "penitent_greaves", "minPercentOfAspect": 50},
            )
        },
        {
            "CountBoots": ItemFilterModel(
                item_type=[ItemType.Boots],
                affix_pool=[
                    AffixFilterCountModel(
                        count=[
                            AffixFilterModel(name="intelligence", want_greater=True),
                            AffixFilterModel(name="movement_speed", want_greater=True),
                            AffixFilterModel(name="lightning_resistance"),
                            AffixFilterModel(name="maximum_life"),
                            AffixFilterModel(name="poison_resistance"),
                            AffixFilterModel(name="shadow_resistance"),
                        ],
                        min_count=3,
                    )
                ],
                unique_aspect={"name": "flickerstep"},
                min_greater_affix_count=2,
            )
        },
        {
            "MultipleAspectsInOneFilter": ItemFilterModel(
                unique_aspect=[
                    AspectUniqueFilterModel(name="battle_trance"),
                    AspectUniqueFilterModel(name="ancients_oath", min_percent_of_aspect=90),
                ]
            )
        },
        {
            "SmallerUniqueAspectValue": ItemFilterModel(
                item_type=[ItemType.Shield], unique_aspect={"name": "crown_of_lucion", "value": 12}
            )
        },
        {"UniqueAspectWithGA": ItemFilterModel(unique_aspect={"name": "flickerstep"}, min_greater_affix_count=2)},
    ],
)

tributes = ProfileModel(
    name="tributes",
    tributes=[
        TributeFilterModel(name="tribute_of_andariel"),
        TributeFilterModel(name="harmony"),
        TributeFilterModel(rarities=[ItemRarity.Legendary, ItemRarity.Unique]),
    ],
)
