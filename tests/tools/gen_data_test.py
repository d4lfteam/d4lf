from src.tools import gen_data


def test_set_tagged_seal_affix_normalises_with_set_name() -> None:
    description = "{c_set}Arms of Arreat{/c}: +{c_number}[Affix_Flat_Value_1]{/c} maximum Resolve"

    assert gen_data.normalise_affix_description(description) == (
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
        if key in gen_data.EXCLUDED_SEAL_AFFIX_KEYS
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
    monkeypatch.setattr(gen_data, "D4LF_BASE_DIR", tmp_path)

    sets = ["existing"]
    sigils = {"minor": {"existing": "Existing"}}

    gen_data.merge_custom_data(sets, "sets", "enUS")
    gen_data.merge_custom_data(sigils, "sigils", "enUS")

    assert sets == ["existing", "new"]
    assert sigils == {"minor": {"existing": "Existing", "new": "New"}, "major": {"boss": "Boss"}}
