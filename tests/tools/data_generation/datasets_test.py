import json

from src.tools.data_generation.affixes import generate_affixes
from src.tools.data_generation.datasets import main, string_list_value


def test_get_string_list_name_returns_a_stable_name() -> None:
    assert string_list_value({"arStrings": [{"szLabel": "name", "szText": "Example"}]}, "name") == "Example"


def test_main_reports_stage_start_finish_counts_and_elapsed_time(tmp_path, monkeypatch, capsys) -> None:
    string_list_dir = tmp_path / "d4data/json/enUS_Text/meta/StringList"
    string_list_dir.mkdir(parents=True)
    (string_list_dir / "UIToolTips.stl.json").write_text('{"arStrings": []}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.tools.data_generation.datasets.D4LF_BASE_DIR", tmp_path)
    for stage in ("aspects", "uniques", "sets", "sigils", "affixes"):
        monkeypatch.setattr(f"src.tools.data_generation.datasets.generate_{stage}", lambda *_args, **_kwargs: 7)

    main(tmp_path / "d4data")

    output = capsys.readouterr().out
    assert "START aspects" in output
    assert "FINISH aspects: 7 files, elapsed=" in output
    assert "FINISH tributes:" in output
    assert "FINISH item_types:" in output
    assert "FINISH tooltips:" in output
    assert "FINISH affixes: 7 files, elapsed=" in output


def test_affix_generation_uses_core_toc_power_index_without_parsing_power_files(tmp_path, monkeypatch) -> None:
    d4data = tmp_path / "d4data"
    string_dir = d4data / "json/enUS_Text/meta/StringList"
    (d4data / "json/base/meta/Affix").mkdir(parents=True)
    (d4data / "json/base/meta/Power").mkdir(parents=True)
    string_dir.mkdir(parents=True)
    empty_strings = '{"arStrings": []}'
    for name in ("AttributeDescriptions", "ItemRequirements", "NecromancerArmy", "SkillTags", "UIToolTips"):
        (string_dir / f"{name}.stl.json").write_text(empty_strings, encoding="utf-8")
    (d4data / "json/base/CoreTOC.dat.json").write_text('{"29": {"42": "Power_example"}}', encoding="utf-8")
    (d4data / "json/GBID.json").write_text("{}", encoding="utf-8")
    (d4data / "json/base/meta/Power/invalid.json").write_text("not json", encoding="utf-8")
    for index in range(3):
        (d4data / f"json/base/meta/Affix/Affix_{index}.json").write_text(
            json.dumps({
                "__fileName__": f"Affix_{index}.json",
                "eMagicType": 0,
                "ptItemAffixAttributes": [{"tAttribute": {"__eAttribute_name__": "Missing"}}],
            }),
            encoding="utf-8",
        )
    output_dir = tmp_path / "assets/lang/enUS"
    output_dir.mkdir(parents=True)
    monkeypatch.setattr("src.tools.data_generation.affixes.D4LF_BASE_DIR", tmp_path)

    sequential = tmp_path / "sequential.json"
    generate_affixes(d4data, "enUS", sequential)

    assert sequential.exists()
