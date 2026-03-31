import numpy as np

from src.config.ui import ResManager
from src.item.descr import texture
from src.template_finder import TemplateMatch


def test_find_affix_bullets_skips_undefined_optional_templates(monkeypatch):
    captured_template_list = []
    monkeypatch.setattr(
        ResManager(),
        "_templates",
        {
            "greater_affix_bullet_point_1_medium": object(),
            "greater_affix_bullet_point_1": object(),
            "greater_affix_bullet_point_masterworked": object(),
            "masterworking_affix_bullet_medium": object(),
            "masterworking_affix_bullet": object(),
            "masterworking_affix_bullet_2": object(),
            "affix_bullet_point_1_medium": object(),
            "affix_bullet_point_1": object(),
            "affix_bullet_point_2_medium": object(),
            "affix_bullet_point_2": object(),
            "rerolled_bullet_point_1_medium": object(),
            "rerolled_bullet_point_1": object(),
            "rerolled_bullet_point_2_medium": object(),
            "rerolled_bullet_point_2": object(),
            "tempered_affix_bullet_point_1_medium": object(),
            "tempered_affix_bullet_point_1": object(),
            "tempered_affix_bullet_point_2_medium": object(),
            "tempered_affix_bullet_point_2": object(),
            "tempered_affix_bullet_point_3_medium": object(),
            "tempered_affix_bullet_point_3": object(),
            "tempered_affix_bullet_point_4_medium": object(),
            "tempered_affix_bullet_point_4": object(),
            "tempered_affix_bullet_point_5_medium": object(),
            "tempered_affix_bullet_point_5": object(),
            "tempered_affix_bullet_point_6_medium": object(),
            "tempered_affix_bullet_point_6": object(),
            "greater_affix_bullet_point_1080p_special": object(),
        },
    )
    monkeypatch.setattr(ResManager(), "_current_resolution", "1920x1080")

    def fake_find_bullets(img_item_descr, sep_short_match, template_list, threshold, mode):
        captured_template_list.extend(template_list)
        return []

    monkeypatch.setattr(texture, "_find_bullets", fake_find_bullets)

    result = texture.find_affix_bullets(np.zeros((5, 5, 3), dtype=np.uint8), TemplateMatch(center=(0, 0)))

    assert result == []
    assert "greater_affix_bullet_point_masterworked_medium" not in captured_template_list
    assert "masterworking_affix_bullet_2_medium" not in captured_template_list
    assert "greater_affix_bullet_point_masterworked" in captured_template_list
    assert "masterworking_affix_bullet_2" in captured_template_list
