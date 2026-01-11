import logging
from copy import deepcopy
from enum import Enum

import cv2
import numpy as np

LOGGER = logging.getLogger(__name__)


class ThresholdTypes(Enum):
    BINARY = 0
    ADAPTIVE = 1
    OTSU = 2


def threshold(
    img: np.ndarray,
    method: ThresholdTypes = ThresholdTypes.BINARY,
    threshold: int = 127,
    inverse: bool = False,
    block_size: int = 1,
    adaptive_thresh_c: int = 10,
) -> np.ndarray:
    """Applies a thresholding method to an input image.

    :param img: Input image to be thresholded. Must be a 3D array representing an RGB image.
    :param method: Thresholding method to use. Options are 'BINARY', 'ADAPTIVE', and 'OTSU'. Default is 'BINARY'.
    :param inverse: Whether to use inverse thresholding. Default is False.
    :param threshold: Threshold value to use for 'BINARY' thresholding. Ignored for other methods. Default is 127.
    :param block_size: Size of a pixel neighborhood that is used to calculate a threshold value for the 'ADAPTIVE' method.
                       Ignored for other methods. Default is 1.
    :param adaptive_thresh_c: Constant subtracted from the mean or weighted mean for the 'ADAPTIVE' method.
                              Ignored for other methods. Default is 10.
    :return: The thresholded image
    """
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    thresh_type = cv2.THRESH_BINARY_INV if inverse else cv2.THRESH_BINARY

    # binary threshold
    if method == ThresholdTypes.BINARY:
        _, thresholded_image = cv2.threshold(img_gray, threshold, 255, thresh_type)
    # adaptive threshold (no inversion option here as it's inherently binary)
    elif method == ThresholdTypes.ADAPTIVE:
        thresholded_image = cv2.adaptiveThreshold(
            img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, adaptive_thresh_c
        )
        if inverse:
            thresholded_image = 255 - thresholded_image
    # otsu threshold
    elif method == ThresholdTypes.OTSU:
        _, thresholded_image = cv2.threshold(img_gray, 0, 255, thresh_type + cv2.THRESH_OTSU)

    return thresholded_image


def crop(img: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    """Cuts an image according to a region of interest.

    :param img: Source image.
    :param roi: Region of interest in the format (x, y, w, h).
    :return: Cropped image.
    """
    x, y, w, h = roi
    height, width = img.shape[:2]

    # Ensure the ROI is within the dimensions of the image
    if x < 0 or y < 0 or x + w > width or y + h > height:
        LOGGER.debug(f"The region of interest {roi} is not within the dimensions of the image {img.shape[:2]}.")
        return img
    return img[y : y + h, x : x + w]


def mask_by_roi(img: np.ndarray, roi: tuple[int, int, int, int], masking_type: str = "regular") -> np.ndarray | None:
    """Masks an image according to a region of interest.

    :param img: Source image.
    :param roi: Region of interest in the format (x, y, w, h).
    :param masking_type: Type of masking, "regular" or "inverse".
    :return: Masked image, or None if type is not recognized.
    """
    x, y, w, h = roi
    if masking_type == "regular":
        masked = np.zeros(img.shape, dtype=np.uint8)
        masked[y : y + h, x : x + w] = img[y : y + h, x : x + w]
    elif masking_type == "inverse":
        masked = img.copy()
        cv2.rectangle(masked, (x, y), (x + w - 1, y + h - 1), (0, 0, 0), -1)
    else:
        LOGGER.error(f"Unrecognized masking type '{masking_type}'.")
        return None
    return masked


def alpha_to_mask(img: np.ndarray) -> np.ndarray | None:
    """Creates a mask from an image where alpha == 0.

    :param img: Source image.
    :return: Mask, or None if the image has no alpha channel or the minimum alpha value is not 0.
    """
    if img.shape[2] == 4 and np.min(img[:, :, 3]) == 0:
        _, mask = cv2.threshold(img[:, :, 3], 1, 255, cv2.THRESH_BINARY)
        return mask
    return None


def create_mask(size: tuple[int, int], roi: tuple[int, int, int, int]) -> np.ndarray:
    """Creates a mask with a specific size and region of interest.

    :param size: Size of the mask.
    :param roi: Region of interest in the format (x, y, w, h).
    :return: Created mask.
    """
    img = np.ones(size[:2], dtype=np.uint8) * 255
    x, y, w, h = roi
    img[y : y + h, x : x + w] = 0
    return img


def color_filter(
    img: np.ndarray, color_range: list[np.ndarray], calc_filtered_img: bool = True
) -> tuple[np.ndarray, np.ndarray | None]:
    color_ranges = []
    # ex: [array([ -9, 201,  25]), array([ 9, 237,  61])]
    if color_range[0][0] < 0:
        lower_range = deepcopy(color_range)
        lower_range[0][0] = 0
        color_ranges.append(lower_range)
        upper_range = deepcopy(color_range)
        upper_range[0][0] = 180 + color_range[0][0]
        upper_range[1][0] = 180
        color_ranges.append(upper_range)
    # ex: [array([ 170, 201,  25]), array([ 188, 237,  61])]
    elif color_range[1][0] > 180:
        upper_range = deepcopy(color_range)
        upper_range[1][0] = 180
        color_ranges.append(upper_range)
        lower_range = deepcopy(color_range)
        lower_range[0][0] = 0
        lower_range[1][0] = color_range[1][0] - 180
        color_ranges.append(lower_range)
    else:
        color_ranges.append(color_range)
    color_masks = []
    hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    for color_range in color_ranges:
        mask = cv2.inRange(hsv_img, color_range[0], color_range[1])
        color_masks.append(mask)
    color_mask = np.bitwise_or.reduce(color_masks) if len(color_masks) > 0 else color_masks[0]
    if calc_filtered_img:
        filtered_img = cv2.bitwise_and(img, img, mask=color_mask)
        return color_mask, filtered_img
    return color_mask, None


def overlay_image(image1: np.ndarray, image2: np.ndarray, x_offset: int, y_offset: int) -> np.ndarray:
    """Overlays two images at specified offsets, creating a combined image.

    :param image1: The first image to be placed on the canvas.
    :param image2: The second image to be overlaid on top of the first one.
    :param x_offset: The horizontal offset of the second image with respect to the first one.
    :param y_offset: The vertical offset of the second image with respect to the first one.
    :return: Combined image with the second image overlaid on top of the first one at the specified offsets.
    """
    # Determine the dimensions of the combined image
    w_combined = max(image1.shape[1] - min(0, x_offset), image2.shape[1] + max(0, x_offset))
    h_combined = max(image1.shape[0] - min(0, y_offset), image2.shape[0] + max(0, y_offset))

    # Create a blank canvas for the combined image
    combined_image = np.zeros((h_combined, w_combined, 3), dtype=np.uint8)

    # Calculate the position to place the first image on the canvas
    x1_offset = max(0, -x_offset)
    y1_offset = max(0, -y_offset)

    # Calculate the position to place the second image on the canvas
    x2_offset = max(0, x_offset)
    y2_offset = max(0, y_offset)

    # Place the first image on the canvas
    combined_image[y1_offset : y1_offset + image1.shape[0], x1_offset : x1_offset + image1.shape[1]] = image1

    # Place the second image on the canvas (taking care of possible overlapping)
    for i in range(image2.shape[0]):
        for j in range(image2.shape[1]):
            y = y2_offset + i
            x = x2_offset + j
            if y < combined_image.shape[0] and x < combined_image.shape[1]:
                combined_image[y, x] = image2[i, j]

    return combined_image


def get_typographic_lines(img: np.ndarray, should_invert: bool = False) -> tuple[int, int, int, int]:
    """Extracts typographic lines from an image containing a single line of text.

    :param img: The input image. Expects an image with light text on a dark background.
    :param should_invert: Whether to invert the image before processing. Set to True if you have dark text on a light background.
    :return: A tuple containing the positions (in y-coordinates) of the topline, baseline, midline, and beardline, respectively.
    """
    # Make img grayscale if it isn't already
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # invert the grayscale image if needed
    if should_invert:
        img = cv2.bitwise_not(img)
    # Threshold the image
    binary_img = threshold(img, method=ThresholdTypes.OTSU)
    # Compute vertical histogram
    histogram = cv2.reduce(binary_img, 1, cv2.REDUCE_SUM, dtype=cv2.CV_32S).flatten()
    # Calculate deltas in histogram
    deltas = np.diff(histogram)
    # Find the first row with text as topline
    topline = np.where(histogram > 0)[0][0]
    # Find the last row with text as beardline (approached from the bottom)
    beardline = np.where(histogram[::-1] > 0)[0][0]
    beardline = len(histogram) - beardline - 1  # Adjust for reversed indexing
    # Identify the two sharpest deltas for midline and baseline
    sharpest_deltas_indices = np.argsort(np.abs(deltas))[-2:]
    # Sort them to determine which is midline and which is baseline
    midline, baseline = sorted(sharpest_deltas_indices)

    return topline, baseline, midline, beardline


def compare_histograms(imageA, imageB):
    histA = cv2.calcHist([imageA], [0], None, [256], [0, 256])
    histB = cv2.calcHist([imageB], [0], None, [256], [0, 256])
    histA = cv2.normalize(histA, histA).flatten()
    histB = cv2.normalize(histB, histB).flatten()

    # Compute correlation between histograms
    return cv2.compareHist(histA, histB, cv2.HISTCMP_CORREL)
