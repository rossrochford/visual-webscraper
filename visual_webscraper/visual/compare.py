import numpy as np
import os

# from skimage.measure import compare_ssim
from skimage.metrics import structural_similarity, mean_squared_error

from scipy.interpolate import interp1d

SUMMARY_WIDTH = 50
SUMMARY_SIZE = SUMMARY_WIDTH*SUMMARY_WIDTH
SUMMARY_SIZE_TRUNC = SUMMARY_SIZE-SUMMARY_WIDTH
HIST_DENOMINATOR = SUMMARY_SIZE*2

IMAGE_SIM_QUANTIZED_NUM_COLOURS = os.environ.get('PNG_QUANT_NUM_COLOURS', 16)


def _compare_summaries(img_data1, img_data2):

    matches1 = np.sum(img_data1['pixelsQ'] == img_data2['pixelsQ'])
    ans1 = 1 - (matches1 / SUMMARY_SIZE)

    matches2 = np.sum(img_data1['pixelsQ_offset50'] == img_data2['pixelsQ_trunc50'])
    ans2 = 1 - (matches2 / SUMMARY_SIZE_TRUNC)

    matches3 = np.sum(img_data1['pixelsQ_trunc50'] == img_data2['pixelsQ_offset50'])
    ans3 = 1 - (matches3 / SUMMARY_SIZE_TRUNC)

    ans = (ans1 * 0.5) + (ans2 * 0.25) + (ans3 * 0.25)

    if ans > 1:
        import pdb; pdb.set_trace()

    return ans


'''

def _compare_summaries(self, other):

    matches1 = np.sum(self.pixels == other.pixels)
    ans1 = 1 - (matches1 / SUMMARY_SIZE)

    matches2 = np.sum(self.pixels_50_offset == other.pixels_truncated)
    ans2 = 1 - (matches2 / SUMMARY_SIZE_TRUNC)

    matches3 = np.sum(self.pixels_truncated == other.pixels_50_offset)
    ans3 = 1 - (matches3 / SUMMARY_SIZE_TRUNC)

    ans = (ans1 * 0.5) + (ans2 * 0.25) + (ans3 * 0.25)

    if ans > 1:
        import pdb; pdb.set_trace()

    return ans
    
'''


def _hist_difference(img_data1, img_data2):
    ans = sum(np.absolute(img_data1['histogram'] - img_data2['histogram'])) / HIST_DENOMINATOR

    for i in range(IMAGE_SIM_QUANTIZED_NUM_COLOURS):
        count1 = img_data1['histogram'][i]
        count2 = img_data2['histogram'][i]

        if count1 > 100 and count2 < 4:
            if count1 > 300:
                ans += 0.15
            else:
                ans += 0.08

        elif count2 > 100 and count1 < 4:

            if count2 > 300:
                ans += 0.15
            else:
                ans += 0.08

    return min(1, ans)


def _get_dimensions_factor(img_data1, img_data2):

    if abs(img_data1['height'] - img_data2['height']) < 3 and abs(img_data1['width'] - img_data2['width']) < 3:
        if img_data1['height'] == img_data2['height']:
            if img_data1['width'] == img_data2['width']:
                return 0.9
            return 0.93
        return 0.97
    return None


def _compare_colours(img_data1, img_data2):

    hist_diff = _hist_difference(img_data1, img_data2)
    summary_diff = _compare_summaries(img_data1, img_data2)
    avg = (hist_diff + summary_diff) / 2

    #num_misses_factor = self._get_num_misses_factor(other)

    #if num_misses_factor:
        #avg *= num_misses_factor

    dimensions_factor = _get_dimensions_factor(img_data1, img_data2)
    if dimensions_factor:
        avg *= dimensions_factor

    min_area = min(img_data1['area'], img_data2['area'])
    if min_area > 0:
        ratio = max(img_data1['area'], img_data2['area']) / min_area
        if ratio > 2.4:
            avg *= 1.15
        elif ratio > 2.85:  # todo: should check this upfront?
            return 1

    return min(1, avg)


def _compare_structure(img_data1, img_data2):

    def do_comparison():

        self_img = img_data1['img_crop_GREY']
        other_img = img_data2['img_crop_GREY']

        width1, width2 = self_img.width, other_img.width
        height1, height2 = self_img.height, other_img.height  #  len(self_img), len(other_img)

        if width1 < 7 or width2 < 7 or height1 < 7 or height2 < 7:
            # structural_similarity won't work with images smaller than 7
            return None

        if width1 != width2 or height1 != height2:
            min_height = min(height1, height2)
            min_width = min(width1, width2)
            crop_box = (0, 0, min_width, min_height)

            self_img = self_img.crop(crop_box)
            other_img = other_img.crop(crop_box)

            self_img_array = np.array(self_img)
            other_img_array = np.array(other_img)
        else:

            self_img_array = img_data1['img_crop_GREY_array']
            other_img_array = img_data2['img_crop_GREY_array']

        try:
            ans = structural_similarity(
                self_img_array, other_img_array
            )
        except:
            import pdb; pdb.set_trace()
            print()

        return 1 - ans

    width_diff = abs(img_data1['width'] - img_data2['width'])
    height_diff = abs(img_data1['height'] - img_data2['height'])

    widths_same = width_diff == 0
    heights_same = height_diff == 0

    widths_similar = width_diff < 5
    heights_similar = height_diff < 5

    if widths_similar and heights_similar:
        return do_comparison()

    if widths_similar:
        if height_diff < 11:
            return do_comparison()
    if widths_same:
        if height_diff < 17:
            return do_comparison()
    if heights_similar:
        if width_diff < 11:
            return do_comparison()
    if heights_same:
        if width_diff < 17:
            return do_comparison()
    return None


def visually_similar(img_data1, img_data2):
    colours_sim = _compare_colours(img_data1, img_data2)

    if colours_sim < 0.25:
        return 0

    structure_sim = _compare_structure(img_data1, img_data2)

    #todo: skip comparison when sizes are very different  (output 0.75?)
    #todo: check for same size and is_photo

    if structure_sim is not None:

        if structure_sim < 0.27:
            return 0

        if abs(structure_sim-colours_sim) < 0.12:
            avg_sim = (structure_sim+colours_sim) / 2
            if avg_sim < 0.5:
                return 0

        if structure_sim < 0.35 and colours_sim > 0.5:
            return 0.5

        if structure_sim < 0.3 and colours_sim < 0.5:
            return 0

        if structure_sim > 0.7:
            return 1

        return 0.5

    if colours_sim < 0.4:
        return 0.25
    if colours_sim < 0.6:
        return 0.5

    return 1


def visually_similar_NEW(img_data1, img_data2):

    if img_data1['dummy'] or img_data2['dummy']:
        return 0.5

    if img_data1['is_photo'] and img_data2['is_photo']:
        width_diff = abs(img_data1['width'] - img_data2['width'])
        height_diff = abs(img_data1['height'] - img_data2['height'])
        if width_diff < 5 and height_diff < 3:
            return 0

    signals = []

    val1 = _compare_summaries(img_data1, img_data2)
    # if val1 < 0.2:
    #     return 0  # short-cut to make computations faster
    if val1 < 0.42:
        signals.append(1)

    val2 = _hist_difference(img_data1, img_data2)
    if val2 is not None:
        if val2 < 0.17:
            signals.append(1)
        if val2 > 0.9:
            signals.append(-0.5)

    val3 = _compare_structure(img_data1, img_data2)
    if val3 is not None:
        if val3 < 0.6:
            signals.append(1)
        if val3 > 0.85:
            signals.append(-1)
        elif val3 > 0.75:
            signals.append(-0.6)

    interp = interp1d((3, -1.5), (0, 1))

    ans = interp(sum(signals))

    if ans < 0.24:
        return 0
    if ans > 0.76:
        return 1

    return 0.5
