from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from src.item.filter.repository import ProfileRulesRepository
from src.profiles import ProfileDocumentStore, ProfileModel

if TYPE_CHECKING:
    from src.settings import Settings


def test_repository_publishes_a_complete_rules_snapshot(tmp_path, monkeypatch) -> None:
    settings = SimpleNamespace(user_dir=tmp_path, general=SimpleNamespace(profiles=["profile"]))
    profile = ProfileModel(name="profile", aspect_upgrades=["accelerating"])
    ProfileDocumentStore(profiles_dir=tmp_path / "profiles", full_dump=False).save_new(
        file_name="profile", profile=profile, source="https://example.invalid"
    )

    def reject_default() -> ProfileDocumentStore:
        message = "repository should use the injected settings directory"
        raise AssertionError(message)

    monkeypatch.setattr(ProfileDocumentStore, "default", staticmethod(reject_default))
    repository = ProfileRulesRepository(lambda: cast("Settings", settings))

    first = repository.load_files()
    second = repository.rules

    assert first is second
    assert second.aspect_upgrade_filters == {"profile": ["accelerating"]}
    assert second.all_file_paths == (tmp_path / "profiles" / "profile.yaml",)
    assert repository.files_loaded


def test_repository_detects_profile_file_changes(tmp_path) -> None:
    settings = SimpleNamespace(user_dir=tmp_path, general=SimpleNamespace(profiles=["profile"]))
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    profile_path = profile_dir / "profile.yaml"
    profile_path.write_text("AspectUpgrades: []\n", encoding="utf-8")
    repository = ProfileRulesRepository(lambda: cast("Settings", settings))

    repository.load_files()
    assert not repository.did_files_change()
    profile_path.write_text("AspectUpgrades:\n- accelerating\n", encoding="utf-8")

    assert repository.did_files_change()


def test_repository_rejects_profile_paths_outside_profiles_directory(tmp_path) -> None:
    user_dir = tmp_path / "user"
    (user_dir / "profiles").mkdir(parents=True)
    external_path = user_dir / "external.yaml"
    ProfileDocumentStore(profiles_dir=user_dir, full_dump=False).save_new(
        file_name="external", profile=ProfileModel(name="external", aspect_upgrades=["accelerating"]), source="test"
    )
    settings = SimpleNamespace(user_dir=user_dir, general=SimpleNamespace(profiles=["../external"]))
    repository = ProfileRulesRepository(lambda: cast("Settings", settings))

    loaded = repository.load_files()

    assert loaded.aspect_upgrade_filters == {}
    assert loaded.all_file_paths == ()
    assert repository.did_files_change()
    external_path.write_text(external_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert not repository.did_files_change()
