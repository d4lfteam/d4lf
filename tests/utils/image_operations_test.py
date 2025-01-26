import numpy as np
import pytest

from src.utils.image_operations import ThresholdTypes, alpha_to_mask, color_filter, create_mask, crop, mask_by_roi, overlay_image, threshold


def test_binary_threshold():
    # Create a dummy 3-channel image
    # Left half is filled with 40s (intensity less than threshold)
    # Right half is filled with 200s (intensity higher than threshold)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :50] = [40, 40, 40]
    img[:, 50:] = [200, 200, 200]

    # Apply binary thresholding with threshold value = 100
    binary_thresh_img = threshold(img, ThresholdTypes.BINARY, threshold=100)

    # Check that left half of image is black
    assert np.all(binary_thresh_img[:, :50] == 0)

    # Check that right half of image is white
    assert np.all(binary_thresh_img[:, 50:] == 255)


def test_crop():
    # Test with a valid ROI
    img = np.zeros((10, 10))
    roi = (2, 2, 6, 6)
    cropped = crop(img, roi)
    assert cropped.shape == (6, 6)

    # Test with an invalid ROI
    roi = (-1, -1, 11, 11)
    cropped = crop(img, roi)
    assert np.array_equal(cropped, img)


def test_mask_by_roi():
    # Test with type "regular" and an image of zeros
    # We create an image of zeros and a region of interest (ROI) in the middle
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    roi = (2, 2, 5, 5)
    # After masking, the image should remain full of zeros, since the ROI is pasted onto a black image
    masked = mask_by_roi(img, roi, "regular")
    # Therefore, the count of non-zero elements should be 0
    assert np.count_nonzero(masked) == 0

    # Test with type "regular" and image of ones
    # We create an image of ones (multiplied by 255 to represent a white image in RGB)
    img = np.ones((10, 10, 3), dtype=np.uint8) * 255
    roi = (2, 2, 5, 5)
    # After masking, only the ROI area should remain white
    masked = mask_by_roi(img, roi, "regular")
    # The number of pixels in the ROI is 5*5 = 25
    # Each pixel has 3 channels (RGB), so the total number of white values should be 25 * 3 = 75
    assert np.count_nonzero(masked) == 25 * 3

    # Test with type "inverse" and an image of ones
    # We create an image of ones (multiplied by 255 to represent a white image in RGB)
    img = np.ones((10, 10, 3), dtype=np.uint8) * 255
    roi = (2, 2, 5, 5)
    # After masking, the ROI area in the image should be blackened out
    masked = mask_by_roi(img, roi, "inverse")
    # The total number of pixels is 10*10 = 100
    # The number of pixels in the ROI is 5*5 = 25
    # So the number of white pixels outside the ROI is 100 - 25 = 75
    # Each pixel has 3 channels (RGB), so the total number of white values should be 75 * 3 = 225
    assert np.count_nonzero(masked) == (100 - 25) * 3

    # Test with type "inverse" and image of zeros
    # We create an image of zeros (a black image in RGB)
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    roi = (2, 2, 5, 5)
    # After masking, the image should remain full of zeros, since the ROI is made black on the already black image
    masked = mask_by_roi(img, roi, "inverse")
    # Therefore, the count of non-zero elements should be 0
    assert np.count_nonzero(masked) == 0

    # Test with unrecognized type
    img = np.ones((10, 10, 3), dtype=np.uint8) * 255
    roi = (2, 2, 5, 5)
    masked = mask_by_roi(img, roi, "unrecognized")
    assert masked is None


def test_alpha_to_mask():
    # Test with an image that has an alpha channel
    img = np.zeros((10, 10, 4), dtype=np.uint8)
    img[0, 0, 3] = 255
    mask = alpha_to_mask(img)
    assert mask is not None

    # Test with an image that does not have an alpha channel
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    assert alpha_to_mask(img) is None


def test_create_mask():
    size = (10, 10)
    roi = (2, 2, 6, 6)
    mask = create_mask(size, roi)
    assert np.count_nonzero(mask) == 100 - 36


@pytest.fixture
def filter_img():
    return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)


@pytest.fixture
def color_range():
    return [np.array([0, 0, 0]), np.array([180, 255, 255])]


def test_color_filter_mask_shape(filter_img, color_range):
    color_mask, _ = color_filter(filter_img, color_range, calc_filtered_img=False)
    assert color_mask.shape == filter_img.shape[:2]


def test_color_filter_no_img(filter_img, color_range):
    _, img = color_filter(filter_img, color_range, calc_filtered_img=False)
    assert img is None


def test_color_filter_with_img(filter_img, color_range):
    _, img = color_filter(filter_img, color_range, calc_filtered_img=True)
    assert isinstance(img, np.ndarray)


def test_overlay_image():
    # Create two sample images of size 10x10
    image1 = np.zeros((10, 10, 3), dtype=np.uint8)
    image2 = np.ones((10, 10, 3), dtype=np.uint8) * 255

    # Define the offsets
    x_offset = 5
    y_offset = 5

    # Call the function to overlay the images
    combined_image = overlay_image(image1, image2, x_offset, y_offset)

    # Check the dimensions of the combined image
    assert combined_image.shape == (15, 15, 3)

    # Check if the first image is properly placed
    assert np.array_equal(combined_image[:10, :5], image1[:, :5])  # Check the non-overlapping part of image1

    # Check if the second image is properly overlaid on top of the first one
    assert np.array_equal(combined_image[5:15, 5:15], image2)  # Check the part where image2 is overlaid

    # Check if the rest of the area is blank
    assert np.all(combined_image[15:] == 0)
    assert np.all(combined_image[:, 15:] == 0)
