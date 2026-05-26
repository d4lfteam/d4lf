SIGIL_RARITY_COLOR_TAGS = {
    "c_white": "Common",
    "c_magic": "Magic",
    "c_rare": "Rare",
    "c_legendary": "Legendary",
    "c_mythic": "Mythic",
}

CROWD_CONTROL_TYPES = {
    0: "CC_Type_Slow",
    1: "CC_Type_Immobilize",
    2: "CC_Type_Stun",
    4: "CC_Type_Taunt",
    5: "CC_Type_Weakened",
    7: "CC_Type_Disabled",
    9: "CC_Type_Chill",
    10: "CC_Type_Frozen",
    11: "CC_Type_Knockback",
    13: "CC_Type_Fear",
}

CROWD_CONTROLLED_TYPES = {
    0: "Affected_By_CC_Type_Slow",
    1: "Affected_By_CC_Type_Immobilize",
    2: "Affected_By_CC_Type_Stun",
    7: "Affected_By_CC_Type_Disabled",
    9: "Affected_By_CC_Type_Chill",
    10: "Affected_By_CC_Type_Frozen",
    11: "Affected_By_CC_Type_Knockdown",
    13: "Affected_By_CC_Type_Fear",
}

DAMAGE_TYPES = {
    0: "Damage_Physical",
    1: "Damage_Fire",
    2: "Damage_Lightning",
    3: "Damage_Cold",
    4: "Damage_Poison",
    5: "Damage_Shadow",
    6: "Damage_Holy",
}

DOT_TYPES = {0: "DOT_Damage_Physical", 1: "DOT_Damage_Fire", 4: "DOT_Damage_Poison", 5: "DOT_Damage_Shadow"}

NECRO_PET_NAMES = {0: "UnitType_Warrior", 1: "UnitType_Mage", 2: "UnitType_Golem"}

RESISTANCE_TYPES = {
    0: "Physical_Gem",
    1: "Fire_Gem",
    2: "Lightning_Gem",
    3: "Cold_Gem",
    4: "Poison_Gem",
    5: "Shadow_Gem",
}

RESOURCE_TYPES = {
    0: "Search_ResourceMana_TagName",
    1: "Search_ResourceFury_TagName",
    3: "Search_ResourceEnergy_TagName",
    5: "Search_ResourceSpirit_TagName",
    6: "Search_ResourceEssence_TagName",
    7: "Search_ResourceVigor_TagName",
    9: "Search_ResourceFaith_TagName",
    10: "Search_ResourceWrath_TagName",
}

SHAPESHIFT_FORMS = {0: "Shapeshift_Form_Human"}

POWER_LOCALISATION_IDS = {
    "AoE_Size_Bonus_Per_Power",
    "Attack_Speed_Percent_Bonus_For_Power",
    "Blood_Orb_Bonus_Chance_Per_Power",
    "Bonus_Count_Per_Power",
    "Bonus_Max_Skill_Charges_For_Power",
    "Bonus_Percent_Per_Power",
    "Bonus_Percent_Per_Power_2",
    "Bonus_Percent_Per_Power_3",
    "CC_Duration_Bonus_Percent_Per_Power",
    "Chance_For_Double_Damage_Per_Power",
    "Chance_To_Consume_No_Charges_Per_Power",
    "Chance_To_Hit_Twice_Per_Power",
    "Cleave_Damage_Bonus_Percent_Per_Power",
    "Combat_Effect_Chance_Bonus_Per_Skill",
    "Damage_Percent_Bonus_While_Affected_By_Power",
    "Movement_Speed_Bonus_Percent_Per_Power",
    "Paladin_Aura_Potency_Per_Skill",
    "Percent_Bonus_Projectiles_Per_Power",
    "Power Bonus Attack Radius Percent",
    "Power_Cooldown_Reduction_Percent",
    "Power_Crit_Percent_Bonus",
    "Power_Damage_Percent_Bonus",
    "Power_Duration_Bonus_Pct",
    "Power_Resource_Cost_Reduction_Percent",
    "Resource_Gain_Bonus_Percent_Per_Power",
    "Skill_Rank_Bonus",
    "Sorc_Conjurations_BonusSummons_Chance",
    "Talent_Rank_Bonus",
}

POWER_SUB_LOCALISATION_IDS = {
    "AoE_Size_Bonus_Per_Power",
    "Bonus_Count_Per_Power",
    "Bonus_Percent_Per_Power",
    "Bonus_Percent_Per_Power_2",
    "Bonus_Percent_Per_Power_3",
    "Chance_To_Hit_Twice_Per_Power",
    "Cleave_Damage_Bonus_Percent_Per_Power",
    "Damage_Percent_Bonus_While_Affected_By_Power",
    "MaxStacks",
    "Movement_Speed_Bonus_Percent_Per_Power",
    "Percent_Bonus_Projectiles_Per_Power",
    "Power_Cooldown_Reduction_Percent",
    "Spiritborn_Spirit_Bonus",
}

SKILL_TAG_LOCALISATION_IDS = {
    "AoE_Size_Bonus_Per_Skill_Tag",
    "Attack_Speed_Percent_Bonus_Per_Skill_Tag",
    "Crit_Damage_Percent_Per_Skill_Tag",
    "Crit_Percent_Bonus_Per_Skill_Tag",
    "Custom_Duration_Bonus_Per_Skill_Tag",
    "Damage_Percent_Bonus_Per_Skill_Tag",
    "Damage_Percent_Bonus_To_Targets_Affected_By_Skill_Tag",
    "Damage_Percent_Reduction_From_Targets_With_Skill_Tag",
    "Generic_Chance_For_Double_Damage_Per_SkillTag",
    "Generic_Chance_For_Hit_Twice_Per_SkillTag",
    "Hit_Effect_Chance_Bonus_Per_Skill_Tag",
    "Overpower_Damage_Percent_Bonus_Per_Skill_Tag",
    "Per_Skill_Tag_Buff_Duration_Bonus_Percent",
    "Percent_Bonus_Projectiles_Per_Skill_Tag",
    "Primary_Resource_On_Cast_Per_Skill_Tag",
    "Skill_Rank_Skill_Tag_Bonus",
    "Skill_Tag_Cooldown_Reduction_Percent",
    "Skill_Tag_Resource_Cost_Reduction_Percent",
    "Resource_Gain_Bonus_Percent_Per_Skill_Tag",
}

SKILL_TAG_SUB_LOCALISATION_IDS = {
    "Damage_Percent_Bonus_Per_Skill_Tag",
    "Damage_Percent_Bonus_To_Targets_Affected_By_Skill_Tag",
}

RESOURCE_LOCALISATION_IDS = {
    "Resource_Cost_Reduction_Percent",
    "Resource_Max_Bonus",
    "Resource_On_Hit",
    "Resource_On_Kill",
    "Resource_On_Kill_Warlock",
    "Resource_Regen_Per_Second",
}

DAMAGE_LOCALISATION_IDS = {
    "Bucketed_Multiplicative_Damage_Type",
    "Combat_Effect_Chance_Bonus_Per_Damage_Type",
    "Damage_Type_Crit_Damage_Percent_Bonus",
    "Damage_Type_Crit_Percent_Bonus_Vs_Elites",
    "Damage_Type_Percent_Bonus",
    "DOT_DPS_Bonus_Percent_Per_Damage_Type",
    "Per_Damage_Type_Buff_Duration_Bonus_Percent",
    "Proc_Flat_Element_Damage_On_Hit",
    "Resistance",
    "Resistance_Max_Bonus",
    "Multiplicative_Damage_Type_Percent_Bonus",
}

CROWD_CONTROLLED_LOCALISATION_IDS = {"Crit_Percent_Bonus_Vs_CC_Target", "Damage_Percent_Bonus_Vs_CC_Target"}

CROWD_CONTROL_LOCALISATION_IDS = {
    "On_Crit_CC_Proc_Chance",
    "On_Hit_CC_Proc_Chance",
    "CC_Duration_Reduction_Per_Type",
    "CC_Duration_Bonus_Percent_Per_Type",
}

WEAPON_TYPE_LOCALISATION_IDS = {
    "Damage_Percent_Bonus_Per_Weapon_Requirement",
    "Overpower_Damage_Percent_Bonus_Per_Weapon_Requirement",
    "Primary_Resource_Gain_Bonus_Percent_Per_Weapon_Requirement",
}

DOT_LOCALISATION_IDS = {"Damage_Percent_Reduction_From_Dotted_Enemy", "Damage_Percent_Bonus_Against_Dot_Type"}

NECRO_PET_LOCALISATION_IDS = {"NecroArmy_Pet_Type_Damage_Bonus_Pct", "NecroArmy_Pet_Type_Inherit_Thorns_Bonus_Pct"}

LOCALISATION_ID_RENAMES = {
    "On_Hit_Vulnerable_Proc_Chance": "On_Hit_Vulnerable_Proc",
    "On_Hit_Vulnerable_Proc_Duration_Seconds": "On_Hit_Vulnerable_Proc",
    "Movement_Bonus_On_Elite_Kill": "Movement_Speed_Bonus_On_Elite_Kill",
    "Movement_Bonus_On_Elite_Kill_Duration": "Movement_Speed_Bonus_On_Elite_Kill",
    "Weapon_On_Hit_Percent_Bleed_Proc_Chance": "Weapon_On_Hit_Percent_Bleed_Proc_Chance_Combined",
    "Weapon_On_Hit_Percent_Bleed_Proc_Damage": "Weapon_On_Hit_Percent_Bleed_Proc_Chance_Combined",
    "Weapon_On_Hit_Percent_Bleed_Proc_Duration": "Weapon_On_Hit_Percent_Bleed_Proc_Chance_Combined",
    "Evade_Movement_Speed": "Evade_Movement_Speed_Combined",
    "Evade_Movement_Speed_Duration": "Evade_Movement_Speed_Combined",
    "Damage_Bonus_On_Elite_Kill": "Damage_Bonus_On_Elite_Kill_Combined",
    "Damage_Bonus_On_Elite_Kill_Duration": "Damage_Bonus_On_Elite_Kill_Combined",
    "Damage_Bonus_Percent_On_Dodge": "Damage_Bonus_Percent_After_Dodge",
    "Damage_Bonus_Percent_On_Dodge_Duration": "Damage_Bonus_Percent_After_Dodge",
    "Attack_Speed_Bonus_On_Dodge": "Attack_Speed_Bonus_After_Dodge",
    "Attack_Speed_Bonus_On_Dodge_Duration": "Attack_Speed_Bonus_After_Dodge",
    "Blood_Orb_Pickup_Damage_Percent_Bonus": "Blood_Orb_Pickup_Damage_Combined",
    "Blood_Orb_Pickup_Damage_Bonus_Duration": "Blood_Orb_Pickup_Damage_Combined",
    "Barrier_When_Struck_Percent_Chance": "Barrier_When_Struck_Chance",
    "Fortified_When_Struck_Percent_Chance": "Fortified_When_Struck_Chance",
    "Fortified_When_Struck_Amount": "Fortified_When_Struck_Chance",
    "On_Hit_Damage_Bonus_Proc_Chance": "On_Hit_Damage_Bonus_Combined",
    "On_Hit_Damage_Bonus_Percent": "On_Hit_Damage_Bonus_Combined",
    "On_Hit_Damage_Bonus_Duration": "On_Hit_Damage_Bonus_Combined",
}

EXPECTED_MISSING_AFFIX_LOCALISATIONS = {
    ("Damage_to_HighLife", "Damage_Bonus_To_High_Health"),
    ("INHERENT_Damage_to_HighLife", "Damage_Bonus_To_High_Health"),
    ("S04_LifePerHit", "Flat_Hitpoints_On_Hit_Unscaled_By_Player_Health"),
    ("S11_LifeOnKill", "Flat_Hitpoints_On_Kill_Unscaled_By_Player_Health"),
    ("S11_LifeOnKill_Greater", "Flat_Hitpoints_On_Kill_Unscaled_By_Player_Health"),
    ("S11_LifeOnKill_Greater_Warlock", "Flat_Hitpoints_On_Kill_Unscaled_By_Player_Health"),
    ("S11_LifeOnKill_Warlock", "Flat_Hitpoints_On_Kill_Unscaled_By_Player_Health"),
    ("S12_KillStreak_Feast_Demons", "S12_KillStreak_Feast_Demons"),
    ("S12_KillStreak_Feast_Evade", "S12_KillStreak_Feast_Evade"),
    ("S12_KillStreak_Hunger_KillstreakRep", "S12_KillStreak_Hunger_KillstreakRep"),
    ("S12_KillStreak_Hunger_KillstreakXP", "S12_KillStreak_Hunger_KillstreakXP"),
    ("Talisman_Charm_CraftingMaterialFind", "Item_Find"),
    ("Talisman_Charm_CraftingMaterialFind_MagicOnly", "Item_Find"),
    ("Tempered_Damage_Generic_LuckHit_Weakened_Tier1", "On_Hit_Weakened_Proc_Chance"),
    ("Tempered_Damage_Generic_LuckHit_Weakened_Tier1", "On_Hit_Weakened_Proc_Duration_Seconds"),
    ("Tempered_Damage_Generic_LuckHit_Weakened_Tier2", "On_Hit_Weakened_Proc_Chance"),
    ("Tempered_Damage_Generic_LuckHit_Weakened_Tier2", "On_Hit_Weakened_Proc_Duration_Seconds"),
    ("Tempered_Damage_Generic_LuckHit_Weakened_Tier3", "On_Hit_Weakened_Proc_Chance"),
    ("Tempered_Damage_Generic_LuckHit_Weakened_Tier3", "On_Hit_Weakened_Proc_Duration_Seconds"),
    ("Test_Warlock_SummonConversationChanceIncrease", "Warlock_SummonConversationChanceIncrease"),
    ("UBERUNIQUE_DamageHealthy_ShatteredVow", "Damage_Bonus_To_High_Health"),
    ("UtilityFind", "Item_Find"),
    ("X2_LifePerHit_2H", "Flat_Hitpoints_On_Hit_Unscaled_By_Player_Health"),
    ("X2_LifePerHit_Greater", "Flat_Hitpoints_On_Hit_Unscaled_By_Player_Health"),
    ("X2_Transfiguration_IncreasedRuneOffering", "Condition_Rune_Scalar"),
    ("X2_Transfiguration_LifePerHit", "Flat_Hitpoints_On_Hit_Unscaled_By_Player_Health"),
    ("X2_Transfiguration_LifePerHit_Lesser", "Flat_Hitpoints_On_Hit_Unscaled_By_Player_Health"),
}
