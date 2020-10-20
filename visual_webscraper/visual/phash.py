from collections import defaultdict

from imagededup.utils.image_utils import preprocess_image
import numpy as np
from PIL import Image
from scipy.fftpack import dct

from util_core.util.file_util import get_files_in_dir


IMAGE_DIR = '/home/ross/code/events_project/webextractor/test_images'

# from imagededup.methods import PHash
# phasher = PHash()
# encodings = phasher.encode_images(image_dir=IMAGE_DIR)
# duplicates = phasher.find_duplicates(encoding_map=encodings)


__coefficient_extract = (8, 8)
TARGET_SIZE = (32, 32)


def _hash_algo(image_array):
    """
    Get perceptual hash of the input image.
    Args:
        image_array: numpy array that corresponds to the image.
    Returns:
        A string representing the perceptual hash of the image.
    """
    dct_coef = dct(dct(image_array, axis=0), axis=1)

    # retain top left 8 by 8 dct coefficients
    dct_reduced_coef = dct_coef[
        : __coefficient_extract[0], : __coefficient_extract[1]
    ]

    # median of coefficients excluding the DC term (0th term)
    # mean_coef_val = np.mean(np.ndarray.flatten(dct_reduced_coef)[1:])
    median_coef_val = np.median(np.ndarray.flatten(dct_reduced_coef)[1:])

    # return mask of all coefficients greater than mean of coefficients
    hash_mat = dct_reduced_coef >= median_coef_val
    return hash_mat


def _array_to_hash(hash_mat: np.ndarray) -> str:
    """
    Convert a matrix of binary numerals to 64 character hash.
    Args:
        hash_mat: A numpy array consisting of 0/1 values.
    Returns:
        An hexadecimal hash string.
    """
    return ''.join('%0.2x' % x for x in np.packbits(hash_mat))


def get_image_phash(pil_img):
    array = preprocess_image(pil_img, target_size=TARGET_SIZE, grayscale=False)
    hash_mat = _hash_algo(array)
    hsh = _array_to_hash(hash_mat)
    return hsh


if __name__ == '__main__':
    fp_by_hash = defaultdict(list)
    for fp in get_files_in_dir(IMAGE_DIR):
        hsh = get_image_phash(Image.open(fp))
        fp_by_hash[hsh].append(fp)

    import pdb; pdb.set_trace()