import logging

import numpy as np

from src.config import AFFIX_COMPARISON_CHARS
from src.dataloader import Dataloader
from src.item.data.aspect import Aspect
from src.item.descr.text import clean_str, closest_match, find_number
from src.item.descr.texture import find_aspect_search_area
from src.template_finder import TemplateMatch
from src.utils.image_operations import crop
from src.utils.ocr.read import image_to_text

LOGGER = logging.getLogger(__name__)


def find_aspect(img_item_descr: np.ndarray, aspect_bullet: TemplateMatch, do_pre_proc: bool = True) -> tuple[Aspect | None, str]:
    if aspect_bullet is None:
        return None, ""

    roi_aspect = find_aspect_search_area(img_item_descr, aspect_bullet)
    img_full_aspect = crop(img_item_descr, roi_aspect)
    concatenated_str = image_to_text(img_full_aspect, do_pre_proc=do_pre_proc).text.lower().replace("\n", " ")
    cleaned_str = clean_str(concatenated_str)

    cleaned_str = cleaned_str[:AFFIX_COMPARISON_CHARS]
    found_key = closest_match(cleaned_str, Dataloader().aspect_unique_dict)
    num_idx = Dataloader().aspect_unique_num_idx

    if found_key is None:
        return None, cleaned_str

    idx = 0
    if len(num_idx[found_key]) > 0:
        idx = num_idx[found_key][0]
    found_value = find_number(concatenated_str, idx)

    LOGGER.debug(f"{found_key}: {found_value}")

    loc = (aspect_bullet.center[0], aspect_bullet.center[1] - 2)
    return Aspect(name=found_key, value=found_value, text=concatenated_str, loc=loc), cleaned_str
