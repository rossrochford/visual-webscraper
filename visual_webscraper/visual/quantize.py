import os
import subprocess

import numpy as np
from PIL.PngImagePlugin import PngImageFile
from PIL import Image

from util_core.util.decorators import cached_property

IMAGE_SIM_QUANTIZED_NUM_COLOURS = os.environ.get('PNG_QUANT_NUM_COLOURS', 16)
PNG_QUANT_PATH = os.environ.get('PNG_QUANT_PATH', '/usr/local/bin/pngquant')  # https://pngquant.org/


def quantize_image(screenshot_path, num_colours=IMAGE_SIM_QUANTIZED_NUM_COLOURS):

    path, ext = os.path.splitext(screenshot_path)
    new_image_path = path + '-or8.png'

    if not os.path.exists(new_image_path):
        subprocess.call(
            [PNG_QUANT_PATH, str(num_colours), '--nofs', screenshot_path]
        )

    return new_image_path


class QuantizedScreenshot(PngImageFile):
    def __init__(self, *args, **kwargs):
        PngImageFile.__init__(self, *args, **kwargs)
        self.filepath = None
        #super(PaletteScreenshot, self).__init__(*args, **kwargs)

    @cached_property
    def palette_colours(self):
        palette = self.palette.palette
        palette_colours = []

        for colour_index in range(0, len(palette), 3):
            curr_colour = []
            for component_index in range(3):
                component_index = colour_index + component_index
                curr_colour.append(palette[component_index])
            palette_colours.append(curr_colour)
        return palette_colours

    @classmethod
    def create(cls, ss_path, quantize=True):
        if quantize:
            ss_path = quantize_image(ss_path)
        quantized_pil_image = Image.open(ss_path)  # note: this would be faster if the data was shared between invocations of LinkElement.description
        quantized_pil_image.__class__ = QuantizedScreenshot
        return quantized_pil_image

    @cached_property
    def image_pixels(self):  # or should we load a 2d array?
        return self.load()

    @cached_property
    def image_pixel_array(self):
        # from: code.activestate.com/recipes/577591-conversion-of-pil-image-and-numpy-array/
        return np.array(self.getdata(), np.uint8).reshape(self.size[0], self.size[1], 1)  # or should reshape be the other way around?

    def show_rect(self, img_rect):
        cropped_image = self.copy()
        cropped_image = cropped_image.crop(
            (img_rect.x, img_rect.y, img_rect.end_x, img_rect.end_y)
        )
        cropped_image.show()

    def create_visual_matrix(self, elem_descriptions, context):
        # old verion:
        # from visual_matrix.util.util import ImageRect  # an older implementation
        # img_pixels = self.image_pixel_array
        # rects = [ImageRect(ld['rect'], img_pixels, img=self) for ld in elem_descriptions]
        rects = create_rects(cls, elem_descriptions, context)
        return create_visual_matrix(rects)