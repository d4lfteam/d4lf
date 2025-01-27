import logging
import threading
import uuid

import cv2
import numpy as np
import tesserocr

from src.config import BASE_DIR
from src.config.data import COLORS
from src.config.helper import singleton
from src.config.loader import IniConfigLoader
from src.utils.image_operations import color_filter
from src.utils.ocr.models import OcrResult

LOGGER = logging.getLogger(__name__)


@singleton
class _APILoader:
    tessdata_path = BASE_DIR / "assets/tessdata"

    def __init__(self):
        self._apis = []
        self._lock = threading.Lock()

    def get_api(self, user: uuid.UUID) -> tesserocr.PyTessBaseAPI:
        with self._lock:
            for api in self._apis:
                if not api["user"]:
                    api["user"] = user
                    return api["api"]
            new_api = tesserocr.PyTessBaseAPI(
                psm=3, oem=tesserocr.OEM.LSTM_ONLY, path=str(self.tessdata_path), lang=IniConfigLoader().general.language
            )
            new_api.SetVariable("debug_file", "/dev/null")
            self._apis.append({"api": new_api, "user": user})
            return new_api

    def release_api(self, user: uuid.UUID) -> None:
        with self._lock:
            for api in self._apis:
                if api["user"] == user:
                    api["user"] = ""
                    return
        LOGGER.warning(f"API for {user} not found!")


def image_to_text(img: np.ndarray, line_boxes: bool = False, do_pre_proc: bool = True) -> OcrResult | tuple[OcrResult, list[int]]:
    my_id = uuid.uuid4()
    api = _APILoader().get_api(my_id)
    if img is None or len(img) == 0:
        LOGGER.warning("img provided to image_to_text() is empty!")
        return OcrResult("", "", word_confidences=0, mean_confidence=0), [] if line_boxes else ""

    # Apply a border to the image. This weird hack prevents the "Error in boxClipToRectangle" errors.
    # Read more here: https://github.com/tesseract-ocr/tesseract/issues/427#issuecomment-248153491
    border_size = 10
    final_img = cv2.copyMakeBorder(
        img,
        top=border_size,
        bottom=border_size,
        left=border_size,
        right=border_size,
        borderType=cv2.BORDER_CONSTANT,
        value=[0, 0, 0],
    )
    if do_pre_proc:
        final_img = _pre_proc_img(img)
    api.SetImageBytes(*_img_to_bytes(final_img))
    text = api.GetUTF8Text().strip()
    res = OcrResult(original_text=text, text=text, word_confidences=api.AllWordConfidences(), mean_confidence=api.MeanTextConf())
    if line_boxes:
        line_boxes_res = api.GetComponentImages(tesserocr.RIL.TEXTLINE, True)
        _APILoader().release_api(my_id)
        return res, line_boxes_res
    _APILoader().release_api(my_id)
    return res


def _img_to_bytes(image: np.ndarray, colorspace: str = "BGR"):
    """
    Convert the given image to bytes suitable for Tesseract.
    :param image: The input image.
    :param colorspace: The color space of the image.
    :return: A tuple containing the image bytes, width, height, bytes per pixel, and bytes per line.
    """
    bytes_per_pixel = image.shape[2] if len(image.shape) == 3 else 1
    height, width = image.shape[:2]
    bytes_per_line = bytes_per_pixel * width
    if bytes_per_pixel > 1 and colorspace != "RGB":
        image = cv2.cvtColor(image, getattr(cv2, f"COLOR_{colorspace}2RGB"))
    elif image.dtype == bool:
        image = np.packbits(image, axis=1)
        bytes_per_line = image.shape[1]
        width = bytes_per_line * 8
        bytes_per_pixel = 0
    return image.tobytes(), width, height, bytes_per_pixel, bytes_per_line


def _pre_proc_img(input_img: np.ndarray) -> np.ndarray:
    img = input_img.copy()
    masked_red, _ = color_filter(img, COLORS.unusable_red, False)
    contours, _ = cv2.findContours(masked_red, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 0), -1)

    # Convert the image to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gamma = 1.8
    gamma_corrected = np.power(gray / 255.0, gamma) * 255.0
    gamma_corrected = gamma_corrected.astype(np.uint8)

    # Apply Gaussian blur to reduce noise and smoothen the image
    blurred = gamma_corrected  # cv2.GaussianBlur(gamma_corrected, (3, 3), 0)

    # Perform morphological operations to further enhance text regions
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    dilated = cv2.dilate(blurred, kernel, iterations=1)
    return cv2.erode(dilated, kernel, iterations=1)
