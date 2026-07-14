import numpy as np

from src.item.data.rarity import ItemRarity
from src.item.find_descr import DescrDetection, find_descr, find_descr_with_diagnostics, get_separator_match_in_crop
from src.template_finder import TemplateMatch


def test_find_descr_uses_shared_core_without_diagnostics(mocker):
    detection = DescrDetection(found=True, rarity=ItemRarity.Legendary, crop_roi=[1, 2, 3, 4])
    core = mocker.patch("src.item.find_descr._find_descr_core", return_value=detection)
    image = object()

    result = find_descr(image, (100, 200))

    assert result == (True, ItemRarity.Legendary, None, [1, 2, 3, 4])
    core.assert_called_once_with(image, (100, 200), collect_diagnostics=False)


def test_find_descr_with_diagnostics_uses_shared_core_with_diagnostics(mocker):
    detection = DescrDetection(found=False, failure_reason="missing_separator")
    core = mocker.patch("src.item.find_descr._find_descr_core", return_value=detection)
    image = object()

    result = find_descr_with_diagnostics(image, (100, 200))

    assert result is detection
    core.assert_called_once_with(image, (100, 200), collect_diagnostics=True)


def test_get_separator_match_in_crop_translates_full_image_coordinates():
    detection = DescrDetection(
        found=True,
        cropped_descr=np.zeros((100, 100, 3), dtype=np.uint8),
        crop_roi=[90, 200, 100, 100],
        separator_match=TemplateMatch(
            center=(110, 220), region=[100, 210, 20, 10], name="item_seperator_short_rare", score=0.9
        ),
    )

    result = get_separator_match_in_crop(detection)

    assert result is not detection.separator_match
    assert result.center == (20, 20)
    assert result.region == [10, 10, 20, 10]
    assert result.name == detection.separator_match.name
    assert result.score == detection.separator_match.score


def test_get_separator_match_in_crop_returns_none_for_invalid_crop():
    detection = DescrDetection(
        found=True,
        cropped_descr=object(),
        crop_roi=[-1, 200, 100, 100],
        separator_match=TemplateMatch(
            center=(10, 220), region=[0, 210, 20, 10], name="item_seperator_short_rare", score=0.9
        ),
    )

    assert get_separator_match_in_crop(detection) is None
