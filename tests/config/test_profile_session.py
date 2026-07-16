from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from src.config.loader import IniConfigLoader
from src.profiles import (
    EmptyError,
    Failed,
    Loaded,
    LoadedProfile,
    ProfileDocumentStore,
    ProfileModel,
    ProfileSession,
    Saved,
    SavedProfile,
    TributeFilterModel,
    ValidationDiffers,
    ValidationError,
    YamlError,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class LastOpenedStore:
    name: str | None = None

    def get(self) -> str | None:
        return self.name

    def set(self, name: str) -> None:
        self.name = name


def _store(tmp_path: Path) -> ProfileDocumentStore:
    return ProfileDocumentStore(profiles_dir=tmp_path / "profiles", full_dump=False)


def _session(tmp_path: Path, last_opened_store: LastOpenedStore) -> ProfileSession:
    return ProfileSession(document_store=_store(tmp_path), last_opened_store=last_opened_store)


def _write_profile(tmp_path: Path, file_name: str, body: str) -> Path:
    path = tmp_path / "profiles" / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_discover_returns_active_and_inactive_profiles(tmp_path: Path) -> None:
    _write_profile(tmp_path, "alpha.yaml", "AspectUpgrades:\n- accelerating\n")
    _write_profile(tmp_path, "beta.yml", "AspectUpgrades:\n- accelerating\n")
    _write_profile(tmp_path, "zeta.yaml", "AspectUpgrades:\n- accelerating\n")
    ini = IniConfigLoader()
    ini._general.profiles = ["beta", "alpha", "beta", "missing"]

    catalog = _session(tmp_path, LastOpenedStore()).discover()

    assert catalog.active == ["beta", "alpha"]
    assert catalog.inactive == ["zeta"]
    assert set(catalog.paths) == {"alpha", "beta", "zeta"}


def test_load_success_tracks_snapshot_and_last_opened(tmp_path: Path) -> None:
    _write_profile(tmp_path, "storm_claw.yaml", "AspectUpgrades:\n- accelerating\n")
    store = LastOpenedStore()
    session = _session(tmp_path, store)

    result = session.load("storm_claw")

    assert isinstance(result, Loaded)
    assert store.get() == "storm_claw"
    model = result.loaded_profile.profile.model_copy(deep=True)
    assert not session.is_dirty(model)
    model.aspect_upgrades.append("snowveiled")
    assert session.is_dirty(model)


def test_load_yaml_error_result(tmp_path: Path) -> None:
    _write_profile(tmp_path, "bad.yaml", "Affixes: [\n")

    result = _session(tmp_path, LastOpenedStore()).load("bad")

    assert isinstance(result, YamlError)


def test_load_empty_error_result(tmp_path: Path) -> None:
    _write_profile(tmp_path, "empty.yaml", "")

    result = _session(tmp_path, LastOpenedStore()).load("empty")

    assert isinstance(result, EmptyError)


def test_load_validation_error_with_guidance(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "legacy.yaml",
        "Affixes:\n"
        "- Ring:\n"
        "    itemType: [ring]\n"
        "    affixPool:\n"
        "    - count:\n"
        "      - {name: strength}\n"
        "      minGreaterAffixCount: 1\n",
    )

    result = _session(tmp_path, LastOpenedStore()).load("legacy")

    assert isinstance(result, ValidationError)
    assert "DELETE THIS LINE" in result.guidance


def test_load_validation_error_without_guidance(tmp_path: Path) -> None:
    _write_profile(tmp_path, "not_a_profile.yaml", "- accelerating\n")

    result = _session(tmp_path, LastOpenedStore()).load("not_a_profile")

    assert isinstance(result, ValidationError)
    assert not result.guidance


def test_load_migrates_list_shaped_tributes_to_single_object(tmp_path: Path) -> None:
    _write_profile(tmp_path, "legacy_tributes.yaml", "Tributes:\n- name: harmony\n- rarity: [legendary]\n")

    result = _session(tmp_path, LastOpenedStore()).load("legacy_tributes")

    assert isinstance(result, Loaded)
    assert isinstance(result.loaded_profile.profile.tributes, TributeFilterModel)


def test_save_returns_saved_and_writes_backup(tmp_path: Path) -> None:
    path = _write_profile(tmp_path, "alpha.yaml", "AspectUpgrades:\n- accelerating\n")
    session = _session(tmp_path, LastOpenedStore())
    loaded = session.load("alpha")
    assert isinstance(loaded, Loaded)

    loaded.loaded_profile.profile.aspect_upgrades.append("snowveiled")
    result = session.save(loaded.loaded_profile.profile)

    assert isinstance(result, Saved)
    assert result.saved.path == path
    backup_path = tmp_path / "profiles" / "backups" / "alpha_original.yaml"
    assert backup_path.exists()


def test_save_returns_validation_differs_and_force_save(tmp_path: Path, monkeypatch) -> None:
    session = _session(tmp_path, LastOpenedStore())
    loaded_path = _write_profile(tmp_path, "alpha.yaml", "AspectUpgrades:\n- accelerating\n")
    loaded = session.load("alpha")
    assert isinstance(loaded, Loaded)
    coerced_model = loaded.loaded_profile.profile.model_copy(deep=True)
    coerced_model.aspect_upgrades.append("snowveiled")
    monkeypatch.setattr("src.profiles.ProfileModel.model_validate", lambda _value: coerced_model)

    first = session.save(loaded.loaded_profile.profile)

    assert isinstance(first, ValidationDiffers)
    assert first.coerced_model == coerced_model
    assert loaded_path.read_text(encoding="utf-8") == "AspectUpgrades:\n- accelerating\n"
    second = session.save(first.coerced_model, force=True)
    assert isinstance(second, Saved)
    assert second.saved.path == loaded_path


def test_save_returns_failed_on_store_error(tmp_path: Path) -> None:
    _write_profile(tmp_path, "alpha.yaml", "AspectUpgrades:\n- accelerating\n")
    base_store = _store(tmp_path)

    class FailingStore(ProfileDocumentStore):
        @override
        def save_existing(
            self, *, loaded: LoadedProfile, profile: ProfileModel, source: str, backup_original: bool = False
        ) -> SavedProfile:
            msg = "boom"
            raise RuntimeError(msg)

    failing_store = FailingStore(profiles_dir=base_store.profiles_dir, full_dump=base_store.full_dump)
    session = ProfileSession(document_store=failing_store, last_opened_store=LastOpenedStore())
    loaded = session.load("alpha")
    assert isinstance(loaded, Loaded)

    result = session.save(loaded.loaded_profile.profile)

    assert isinstance(result, Failed)
    assert str(result.error) == "boom"
