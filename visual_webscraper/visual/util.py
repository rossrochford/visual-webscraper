import datetime
import os
import uuid

import numpy as np

from skimage.measure import compare_ssim

SUMMARY_WIDTH = 50
SUMMARY_SIZE = SUMMARY_WIDTH*SUMMARY_WIDTH
SUMMARY_SIZE_TRUNC = SUMMARY_SIZE-SUMMARY_WIDTH
HIST_DENOMINATOR = SUMMARY_SIZE*2

# todo: ensure this is the same as quantize image num_colours parameter
IMAGE_SIM_QUANTIZED_NUM_COLOURS = os.environ.get('PNG_QUANT_NUM_COLOURS', 16)


class ImageRect(object):

    def __init__(self, rect, context):

        # should really check x_end, y_end
        if rect['x'] < 0 or rect['y'] < 0 or rect['height'] == 0 or rect['width'] == 0:
            self.dummy = True
            return
        self.dummy = False

        #self.outer_html = outer_html

        self.imageQ = context['screenshotQ_obj']
        self.image = context['screenshot_obj']

        self.rect = rect
        self.width, self.height = int(rect['width']), int(rect['height'])
        self.area = self.width * self.height  # todo: temporary
        self.box = (
            rect['x'], rect['y'], rect['x'] + rect['width'],
            rect['y'] + rect['height']
        )

        self.rect_Qimg_orig = self.imageQ.crop(self.box)

        self.rect_img_grey = self.image.crop(self.box).convert('L')

        self.rect_img = self.rect_Qimg_orig.resize(
            (SUMMARY_WIDTH, SUMMARY_WIDTH), resample=3
        )
        self.histogram = np.array(self.rect_img.histogram()[:IMAGE_SIM_QUANTIZED_NUM_COLOURS])

        self.pixels = np.array(self.rect_img)
        # NOTE: necessary because the algorithms were writen for a 1d array
        self.pixels = self.pixels.reshape((2500,))

        self.pixels_50_offset = self.pixels[50:]
        self.pixels_truncated = self.pixels[:-50]

        # self.image_rgb = self.image.convert('RGB')
        # self.imageQ_rgb = self.imageQ.convert('RGB')
        #
        # if self._is_photo():
        #     self.show(); other.show()
        #     import pdb; pdb.set_trace()

    def show(self):
        if self.dummy:
            print('cannot show dummy image')
            return
        self.rect_Qimg_orig.show()

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

    def _hist_difference(self, other):
        ans = sum(np.absolute(self.histogram - other.histogram)) / HIST_DENOMINATOR
        return min(1, ans)

    '''
    # no longer needed, gives almost exactly same result at _hist_difference but 
    # takes twice as long to execute
    def _hist_intersection(self, other):
        minima = np.minimum(self.histogram, other.histogram)
        intersection = np.true_divide(np.sum(minima), np.sum(other.histogram))
        return 1 - intersection
    '''

    def _get_num_misses_factor(self, other): # todo: is the strength of this signal affected by the number of colours?
        hist1 = self.histogram
        hist2 = other.histogram
        num_misses = 0

        def miss_val(val1, val2):
            mn_val, mx_val = min(val1, val2), max(val1, val2)
            if mx_val / (mn_val or 0.1) > 3.6:
                return 0.6
            if mx_val - mn_val > 850:
                return 1
            if mx_val > 180 and mn_val < 22:
                return 1
            return 0

        for i in range(10):
            num_misses += miss_val(hist1[i], hist2[i])

        if num_misses > 3.85:
            return 1.5
        elif num_misses > 2.2:
            return 1.25
        elif num_misses < 0.6:
            return 0.48
        elif num_misses < 1.3:
            return 0.6

        return None

    def _get_dimensions_factor(self, other):
        if abs(self.height-other.height) < 3 and abs(self.width-other.width) < 3:
            if self.height == other.height:
                if self.width == other.width:
                    return 0.9
                return 0.93
            return 0.97
        return None

    def save_crop(self, dir):
        if not os.path.exists(dir):
            os.makedirs(dir)
        crop = self.imageQ.copy().crop(self.box)
        path = os.path.join(dir, uuid.uuid4().hex+'.png')
        crop.save(path)
        return path

    def _is_photo(self):

        if self.dummy or self.area < 3000:
            return False
        if '<img' not in self.outer_html and '.jpg' not in self.outer_html and '.png' not in self.outer_html:
            return False
        import pdb; pdb.set_trace()
        pixels_orig = np.array(self.image_rgb.crop(self.box), dtype=np.int16)
        pixels_quant = np.array(self.imageQ_rgb.crop(self.box), dtype=np.int16)
        num_pixels = pixels_orig.shape[0] * pixels_orig.shape[1]

        diffs_matrix = np.abs(pixels_orig - pixels_quant)

        num_equal = (np.mean(diffs_matrix, axis=2) < 7).sum()

        proportion_equal = num_equal / num_pixels

        is_photo = 0.05 < proportion_equal < 0.31

        return is_photo

    def _compare_colours(self, other):

        if self.dummy or other.dummy:
            return 0.5

        # if self.is_photo and other.is_photo and (abs(self.width-other.width) < 5 or abs(self.height-other.height) < 5):
        #     return 0, 1

        hist_diff = self._hist_difference(other)
        summary_diff = self._compare_summaries(other)
        avg = (hist_diff + summary_diff) / 2

        num_misses_factor = self._get_num_misses_factor(other)

        if num_misses_factor:
            avg *= num_misses_factor

        dimensions_factor = self._get_dimensions_factor(other)
        if dimensions_factor:
            avg *= dimensions_factor

        min_area = min(self.area, other.area)
        if min_area > 0:
            ratio = max(self.area, other.area) / min_area
            if ratio > 2.4:
                avg *= 1.15
            elif ratio > 2.85:
                return 1

        return min(1, avg)

    def _compare_structure(self, other):

        # todo: check performance penalty of this function
        # the only time we hit a signal is when the size is similar
        # and
        if self.dummy or other.dummy:
            return None

        def do_comparison():

            self_img = self.rect_img_grey
            other_img = other.rect_img_grey

            width1, width2 = self_img.width, other_img.width
            height1, height2 = self_img.height, other_img.height  #  len(self_img), len(other_img)

            if width1 < 7 or width2 < 7 or height1 < 7 or height2 < 7:
                # compare_ssim won't work with images smaller than 7
                return None

            if width1 != width2 or height1 != height2:
                min_height = min(height1, height2)
                min_width = min(width1, width2)
                crop_box = (0, 0, min_width, min_height)

                self_img = self_img.crop(crop_box)
                other_img = other_img.crop(crop_box)

            # min_width = min(self.width, other.width)
            # min_height = min(self.height, other.height)
            #
            # if self.width == other.width and self.height == other.height:
            #     self_img = self.rect_img_grey
            #     other_img = other.rect_img_grey
            # else:
            #     crop_box = (0, 0, min_width, min_height)
            #
            #     self_img = self.rect_img_grey.crop(crop_box)
            #     other_img = other.rect_img_grey.crop(crop_box)

            self_img = np.array(self_img)
            other_img = np.array(other_img)
            try:
                ans = compare_ssim(self_img, other_img)
            except:
                import pdb; pdb.set_trace()
                print()

            return 1-ans

        widths_same = abs(self.width - other.width) == 0
        heights_same = abs(self.height - other.height) == 0

        widths_similar = abs(self.width-other.width) < 5
        heights_similar = abs(self.height-other.height) < 5

        if widths_similar and heights_similar:
            return do_comparison()

        if widths_similar:
            if abs(self.height-other.height) < 11:
                return do_comparison()
        if widths_same:
            if abs(self.height-other.height) < 17:
                return do_comparison()
        if heights_similar:
            if abs(self.width-other.width) < 11:
                return do_comparison()
        if heights_same:
            if abs(self.width-other.width) < 17:
                return do_comparison()
        return None

    def compare(self, other):
        colours_sim = self._compare_colours(other)

        if colours_sim < 0.25:
            return 0

        structure_sim = self._compare_structure(other)

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
