from dataclasses import dataclass

from src import importing, paragon, perception
from src.item import Filter, ItemType
from src.profiles import ProfileDocumentStore, ProfileModel


def test_imported_profile_round_trips_typed_paragon_and_transforms_board(tmp_path):
    payload = {
        "Name": "Imported build",
        "Source": "fixture",
        "ParagonBoardsList": [[{"Name": "Start", "Rotation": 90, "Nodes": [False] * 441}]],
    }

    @dataclass
    class FakeSource:
        name: str = "fixture"

        def fetch_variants(self, request) -> list[importing.VariantMetadata]:
            return []

        def import_build(self, request, selected_variant_ids=None):
            return importing.ImportResult(
                source_name=self.name,
                selected_variant="default",
                profile=ProfileModel(name="imported", Paragon=payload),
            )

    result = importing.import_build(importing.ImportRequest("fixture://build"), FakeSource())
    store = ProfileDocumentStore(tmp_path / "profiles", full_dump=False)
    saved = store.save_new(file_name="imported", profile=result.profile, source=result.source_name)
    loaded = store.load(saved.path).profile

    assert loaded.paragon is not None
    assert loaded.paragon.paragon_boards_list[0][0].rotation == "90°"
    rotation = paragon.parse_rotation(loaded.paragon.paragon_boards_list[0][0].rotation)
    assert paragon.transform_flat_index(1, rotation // 90) == 41


def test_perception_item_is_evaluated_by_public_filter_facade():
    item = perception.parse_item_text(["GREATER MATERIALS CACHE", "Legendary Cache"])
    assert item is not None
    assert item.item_type == ItemType.Cache
    assert Filter().should_keep(item).keep is False
