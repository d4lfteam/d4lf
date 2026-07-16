from types import SimpleNamespace

from src.dataloader import Dataloader
from src.gui.importer.import_pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter, Variant
from src.gui.importer.importer_config import FilenamePart, ImportConfig
from src.item.data.item_type import ItemType
from src.profiles import ItemFilterModel


def _config(**overrides) -> ImportConfig:
    config = ImportConfig(
        url="https://example.invalid/build",
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=False,
        require_greater_affixes=False,
        export_paragon=False,
    )
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def _item_filter(item_type: ItemType) -> ItemFilterModel:
    return ItemFilterModel(item_type=[item_type], min_power=100)


def _build(**overrides) -> ExtractedBuild:
    build = ExtractedBuild(
        source_name="maxroll",
        class_name="Spiritborn",
        build_header="Touch of Death",
        season_number="12",
        variants=[Variant(name="Pit Push", affix_filters=[_item_filter(ItemType.Ring)])],
    )
    for key, value in overrides.items():
        setattr(build, key, value)
    return build


def _paragon_steps() -> list[list[dict[str, object]]]:
    return [[{"Name": "spiritborn-starting-board", "Glyph": "", "Rotation": "0°", "Nodes": [False] * 441}]]


def test_run_saves_single_variant_and_attaches_paragon(mock_ini_loader, mocker) -> None:
    Dataloader()
    saved = {}
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda *, file_name, profile, source: (
        saved.update({"file_name": file_name, "profile": profile, "source": source})
        or SimpleNamespace(file_name=file_name)
    )
    add_to_profiles = mocker.patch("src.gui.importer.import_pipeline.add_to_profiles")
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)

    saved_file_names = ImportPipeline.run(
        StaticBuildGuideAdapter(
            url="https://example.invalid/build",
            build=_build(
                variants=[
                    Variant(
                        name="Pit Push",
                        affix_filters=[_item_filter(ItemType.Ring)],
                        aspect_upgrade_filters=["accelerating"],
                        paragon_steps=_paragon_steps(),
                        paragon_build_name="Touch of Death Pit Push",
                    )
                ]
            ),
        ),
        _config(export_paragon=True),
    )

    assert saved_file_names == ["maxroll_s12_spiritborn_touch_of_death_pit_push"]
    assert saved["source"] == "https://example.invalid/build"
    assert saved["file_name"] == "maxroll_s12_spiritborn_touch_of_death_pit_push"
    assert saved["profile"].aspect_upgrades == ["accelerating"]
    assert saved["profile"].paragon is not None
    assert saved["profile"].paragon.name == "Touch of Death Pit Push"
    add_to_profiles.assert_not_called()


def test_run_saves_multiple_variants_and_adds_profiles(mock_ini_loader, mocker) -> None:
    Dataloader()
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda *, file_name, profile, source: SimpleNamespace(file_name=file_name)  # noqa: ARG005
    add_to_profiles = mocker.patch("src.gui.importer.import_pipeline.add_to_profiles")
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)

    saved_file_names = ImportPipeline.run(
        StaticBuildGuideAdapter(
            url="https://example.invalid/build",
            build=_build(
                variants=[
                    Variant(name="Variant One", affix_filters=[_item_filter(ItemType.Ring)]),
                    Variant(name="Variant Two", affix_filters=[_item_filter(ItemType.Amulet)]),
                ]
            ),
        ),
        _config(add_to_profiles=True),
    )

    assert saved_file_names == [
        "maxroll_s12_spiritborn_touch_of_death_variant_one",
        "maxroll_s12_spiritborn_touch_of_death_variant_two",
    ]
    assert [call.kwargs["file_name"] for call in profile_store.save_new.call_args_list] == saved_file_names
    assert [call.args[0] for call in add_to_profiles.call_args_list] == saved_file_names


def test_run_suffixes_custom_filename_for_multiple_variants(mock_ini_loader, mocker) -> None:
    Dataloader()
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda *, file_name, profile, source: SimpleNamespace(file_name=file_name)  # noqa: ARG005
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)

    saved_file_names = ImportPipeline.run(
        StaticBuildGuideAdapter(
            url="https://example.invalid/build",
            build=_build(
                variants=[
                    Variant(name="Variant One", affix_filters=[_item_filter(ItemType.Ring)]),
                    Variant(name="Variant Two", affix_filters=[_item_filter(ItemType.Amulet)]),
                ]
            ),
        ),
        _config(custom_file_name="custom-name"),
    )

    assert saved_file_names == ["custom-name_1", "custom-name_2"]


def test_run_uses_selected_filename_parts(mock_ini_loader, mocker) -> None:
    Dataloader()
    saved = {}
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda *, file_name, profile, source: (  # noqa: ARG005
        saved.update({"file_name": file_name}) or SimpleNamespace(file_name=file_name)
    )
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)

    ImportPipeline.run(
        StaticBuildGuideAdapter(url="https://example.invalid/build", build=_build()),
        _config(filename_parts=(FilenamePart.SOURCE, FilenamePart.BUILD_TITLE)),
    )

    assert saved["file_name"] == "maxroll_touch_of_death"


def test_run_warns_when_paragon_export_enabled_without_steps(mock_ini_loader, mocker, caplog) -> None:
    Dataloader()
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda *, file_name, profile, source: SimpleNamespace(file_name=file_name)  # noqa: ARG005
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)

    with caplog.at_level("WARNING"):
        ImportPipeline.run(
            StaticBuildGuideAdapter(url="https://example.invalid/build", build=_build()), _config(export_paragon=True)
        )

    assert "Paragon export enabled, but no paragon data was found" in caplog.text


def test_run_deduplicates_identical_affix_filters(mock_ini_loader, mocker) -> None:
    Dataloader()
    saved = {}
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda *, file_name, profile, source: (  # noqa: ARG005
        saved.update({"profile": profile}) or SimpleNamespace(file_name=file_name)
    )
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)

    ImportPipeline.run(
        StaticBuildGuideAdapter(
            url="https://example.invalid/build",
            build=_build(
                variants=[
                    Variant(name="Pit Push", affix_filters=[_item_filter(ItemType.Ring), _item_filter(ItemType.Ring)])
                ]
            ),
        ),
        _config(),
    )

    assert len(saved["profile"].affixes) == 1
    assert next(iter(saved["profile"].affixes[0].root)) == "Ring(x2)"
