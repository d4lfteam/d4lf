from typing import TYPE_CHECKING

from src.tools.data_generation import affix_helpers
from src.tools.data_generation.affixes import EXCLUDED_SEAL_AFFIX_KEYS, merge_custom_data, normalise_affix_description

if TYPE_CHECKING:
    from src.tools.data_generation.common import AffixGenerationContext


def test_power_name_projection_is_lazy_and_cached_for_one_run(tmp_path, monkeypatch) -> None:
    power_file = tmp_path / "json/enUS_Text/meta/StringList/Power_example.stl.json"
    power_file.parent.mkdir(parents=True)
    power_file.write_text('{"arStrings": [{"szLabel": "name", "szText": "Example Skill"}]}', encoding="utf-8")
    context: AffixGenerationContext = {
        "attribute_descriptions": {},
        "attribute_prefixes": set(),
        "item_requirements": {},
        "necromancer_army": {},
        "power_by_sno": {42: "example.json"},
        "power_names_by_id": {},
        "skill_tags": {},
        "skill_tags_by_sno": {},
        "ui_tooltips": {},
        "weapon_types_by_sno": {},
    }
    load_count = 0
    original_map = affix_helpers.string_list_map

    def counted_map(path):
        nonlocal load_count
        load_count += 1
        return original_map(path)

    monkeypatch.setattr(affix_helpers, "string_list_map", counted_map)

    assert context["power_names_by_id"] == {}
    assert affix_helpers.replace_power_placeholder("Use {VALUE1}", 42, tmp_path, "enUS", context) == "Use Example Skill"
    assert affix_helpers.replace_power_placeholder("Use {VALUE1}", 42, tmp_path, "enUS", context) == "Use Example Skill"
    assert load_count == 1


def test_missing_power_name_is_not_negative_cached(tmp_path, capsys) -> None:
    context: AffixGenerationContext = {
        "attribute_descriptions": {},
        "attribute_prefixes": set(),
        "item_requirements": {},
        "necromancer_army": {},
        "power_by_sno": {42: "missing.json"},
        "power_names_by_id": {},
        "skill_tags": {},
        "skill_tags_by_sno": {},
        "ui_tooltips": {},
        "weapon_types_by_sno": {},
    }

    affix_helpers.replace_power_placeholder("Use {VALUE1}", 42, tmp_path, "enUS", context)
    affix_helpers.replace_power_placeholder("Use {VALUE1}", 42, tmp_path, "enUS", context)

    assert capsys.readouterr().out.count("Could not find file named") == 2


def test_set_tagged_seal_affix_normalises_with_set_name() -> None:
    description = "{c_set}Arms of Arreat{/c}: +{c_number}[Affix_Flat_Value_1]{/c} maximum Resolve"

    assert normalise_affix_description(description) == (
        "arms_of_arreat_maximum_resolve",
        "arms of arreat maximum resolve",
    )


def test_excluded_seal_affix_patterns_match_charm_set_powers() -> None:
    excluded_keys = [
        "when_you_gain_a_stack_of_stoicism_gain_damage_for_second",
        "while_at_least_might_charms_equipped_all_your_damage_bonuses_are_equal_to_your_highest_damage_type_bonus",
        "while_bravery_charm_equipped_every_critical_strike_grants_you_critical_strike_damage_for_seconds_up_to",
        "while_in_a_feral_rage_your_werewolf_skills_gain_attack_speed",
    ]

    assert [
        key
        for key in excluded_keys
        if key in EXCLUDED_SEAL_AFFIX_KEYS
        or (key.startswith("while_at_least_") and "_charms_equipped_" in key)
        or "_charm_equipped_" in key
    ] == excluded_keys


def test_merge_custom_data_handles_list_and_nested_overrides(tmp_path, monkeypatch) -> None:
    custom_file = tmp_path / "src/tools/data/custom_enUS.json"
    custom_file.parent.mkdir(parents=True)
    custom_file.write_text(
        '{"sets": ["existing", "new"], "sigils": {"minor": {"new": "New"}, "major": {"boss": "Boss"}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr("src.tools.data_generation.affixes.D4LF_BASE_DIR", tmp_path)

    sets = ["existing"]
    sigils = {"minor": {"existing": "Existing"}}

    merge_custom_data(sets, "sets", "enUS")
    merge_custom_data(sigils, "sigils", "enUS")

    assert sets == ["existing", "new"]
    assert sigils == {"minor": {"existing": "Existing", "new": "New"}, "major": {"boss": "Boss"}}
