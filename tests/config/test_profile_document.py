from typing import TYPE_CHECKING

import pytest

from src.config.profile_document import ProfileDocumentStore, ProfileValidationError
from src.config.profile_models import ProfileModel

if TYPE_CHECKING:
    from pathlib import Path


def test_load_derives_profile_name_from_file_stem(tmp_path: Path) -> None:
    profile_path = tmp_path / "profiles" / "storm_claw.yaml"
    profile_path.parent.mkdir()
    profile_path.write_text("AspectUpgrades:\n- accelerating\n", encoding="utf-8")

    loaded = ProfileDocumentStore(profiles_dir=tmp_path / "profiles", full_dump=False).load(profile_path)

    assert loaded.path == profile_path
    assert loaded.name == "storm claw"
    assert loaded.profile == ProfileModel(name="storm claw", AspectUpgrades=["accelerating"])


def test_save_new_normalizes_file_name_and_owns_yaml_format(tmp_path: Path) -> None:
    store = ProfileDocumentStore(profiles_dir=tmp_path / "profiles", full_dump=False)
    profile = ProfileModel(name="display name", AspectUpgrades=["snowveiled", "accelerating"])

    saved = store.save_new(file_name="Rob's Cpt. America", profile=profile, source="https://example.invalid")

    assert saved.file_name == "Robs_Cpt_America"
    assert saved.path == tmp_path / "profiles" / "Robs_Cpt_America.yaml"
    assert "# https://example.invalid\n" in saved.path.read_text(encoding="utf-8")
    assert "aspect_upgrades:\n- accelerating\n- snowveiled\n" in saved.path.read_text(encoding="utf-8")


def test_save_existing_writes_loaded_path_and_preserves_original_backup_once(tmp_path: Path) -> None:
    profile_path = tmp_path / "profiles" / "custom_name.yml"
    profile_path.parent.mkdir()
    profile_path.write_text("AspectUpgrades:\n- accelerating\n", encoding="utf-8")
    store = ProfileDocumentStore(profiles_dir=tmp_path / "profiles", full_dump=False)
    loaded = store.load(profile_path)

    store.save_existing(
        loaded=loaded,
        profile=ProfileModel(name="custom name", AspectUpgrades=["snowveiled"]),
        source="custom",
        backup_original=True,
    )
    store.save_existing(
        loaded=loaded,
        profile=ProfileModel(name="custom name", AspectUpgrades=["accelerating", "snowveiled"]),
        source="custom",
        backup_original=True,
    )

    assert profile_path.read_text(encoding="utf-8").startswith("# custom\n")
    assert "aspect_upgrades:\n- accelerating\n- snowveiled\n" in profile_path.read_text(encoding="utf-8")
    backup_path = tmp_path / "profiles" / "backups" / "custom_name_original.yaml"
    assert backup_path.read_text(encoding="utf-8") == "AspectUpgrades:\n- accelerating\n"


def test_load_reports_legacy_validation_guidance_with_stable_code(tmp_path: Path) -> None:
    profile_path = tmp_path / "profiles" / "legacy.yaml"
    profile_path.parent.mkdir()
    profile_path.write_text(
        "Affixes:\n"
        "- Ring:\n"
        "    itemType: [ring]\n"
        "    affixPool:\n"
        "    - count:\n"
        "      - {name: strength}\n"
        "      minGreaterAffixCount: 1\n",
        encoding="utf-8",
    )

    with pytest.raises(ProfileValidationError) as exc_info:
        ProfileDocumentStore(profiles_dir=tmp_path / "profiles", full_dump=False).load(profile_path)

    assert exc_info.value.code == "pool_min_greater_affix_count_legacy"
    assert "DELETE THIS LINE" in exc_info.value.guidance
    assert str(profile_path) in exc_info.value.guidance


def test_load_rejects_non_mapping_yaml_as_document_error(tmp_path: Path) -> None:
    profile_path = tmp_path / "profiles" / "not_a_profile.yaml"
    profile_path.parent.mkdir()
    profile_path.write_text("- accelerating\n", encoding="utf-8")

    with pytest.raises(ProfileValidationError) as exc_info:
        ProfileDocumentStore(profiles_dir=tmp_path / "profiles", full_dump=False).load(profile_path)

    assert exc_info.value.code == "profile_validation_error"
    assert str(profile_path) in str(exc_info.value)
