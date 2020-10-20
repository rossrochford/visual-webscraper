import os

import numpy as np

IMAGE_SIM_QUANTIZED_NUM_COLOURS = os.environ.get('PNG_QUANT_NUM_COLOURS', 16)


def _is_photo(ed, img_crop_RGB, img_cropQ_RGB):
    # if self.dummy or self.area < 3000:
    #     return False
    outer_html = ed['outer_htmlL']
    if '<img' not in outer_html and '.jpg' not in outer_html and '.png' not in outer_html:
        return False

    pixels_orig = np.array(img_crop_RGB, dtype=np.int16)
    pixels_quant = np.array(img_cropQ_RGB, dtype=np.int16)

    num_pixels = pixels_orig.shape[0] * pixels_orig.shape[1]

    diffs_matrix = np.abs(pixels_orig - pixels_quant)

    num_equal = (np.mean(diffs_matrix, axis=2) < 7).sum()

    proportion_equal = num_equal / num_pixels

    is_photo = 0.05 < proportion_equal < 0.31

    return is_photo


def create_screenshot_context(image, imageQ):

    image_rgb = image.convert('RGB')
    imageQ_rgb = imageQ.convert('RGB')

    return {
        'image': image,
        'imageQ': imageQ,
        'image_rgb': image_rgb,
        'imageQ_rgb': imageQ_rgb
    }


def get_img_data(ed, ctx):

    rect = ed['rect']

    if rect['x'] < 0 or rect['y'] < 0 or rect['height'] == 0 or rect['width'] == 0:
        return {'dummy': True}

    box = (
        rect['x'], rect['y'], rect['x'] + rect['width'],
        rect['y'] + rect['height']
    )
    img_crop = ctx['image'].crop(box)
    img_cropQ = ctx['imageQ'].crop(box)
    img_crop_GREY = img_crop.convert('L')
    img_crop_RGB = ctx['image_rgb'].crop(box)
    img_cropQ_RGB = ctx['imageQ_rgb'].crop(box)

    is_photo = False
    if rect['area'] > 5000:
        is_photo = _is_photo(ed, img_crop_RGB, img_cropQ_RGB)

    # hsh = get_image_phash(img_crop)

    imgQ_50x50 = img_cropQ.resize((50, 50), resample=3)
    histogram = np.array(imgQ_50x50.histogram()[:IMAGE_SIM_QUANTIZED_NUM_COLOURS])

    pixelsQ = np.array(imgQ_50x50)
    # NOTE: necessary because the algorithms were writen for a 1d array
    pixelsQ = pixelsQ.reshape((2500,))

    pixelsQ_offset50 = pixelsQ[50:]
    pixelsQ_trunc50 = pixelsQ[:-50]

    img_crop_GREY_array = np.array(img_crop_GREY)

    return {
        'dummy': False,
        'width': rect['width'],
        'height': rect['height'],
        'area': rect['area'],

         #'phash': hsh,
        'is_photo': is_photo,

        'img_crop': img_crop,
        'img_cropQ': img_cropQ,
        'img_crop_RGB': img_crop_RGB,
        'img_cropQ_RGB': img_cropQ_RGB,
        'img_crop_GREY': img_crop_GREY,
        'img_crop_GREY_array': img_crop_GREY_array,

        'histogram': histogram,
        'pixelsQ': pixelsQ,
        'pixelsQ_offset50': pixelsQ_offset50,
        'pixelsQ_trunc50': pixelsQ_trunc50,
    }


IMAGE_FP = '/home/ross/code/events_project/webextractor/webextractor/clustering/ground_truth/data/cluster_data/000c70a1446d7758393193223ce93a08.png'
IMAGE_Q_FP = '/home/ross/code/events_project/webextractor/webextractor/clustering/ground_truth/data/cluster_data/000c70a1446d7758393193223ce93a08_Q.png'
GT_FP = '/home/ross/code/events_project/webextractor/webextractor/clustering/ground_truth/data/cluster_data/000c70a1446d7758393193223ce93a08.json'

from PIL import Image
from webextractor.visual.quantize import QuantizedScreenshot
import json

from webextractor.clustering.util import Cluster
from webextractor.visual.compare import _compare_summaries, _hist_difference, _compare_structure, _compare_colours
from util_core.util.draw import draw_clusters_image2


def main():
    image = Image.open(IMAGE_FP)
    imageQ = QuantizedScreenshot.create(IMAGE_Q_FP, quantize=False)

    ground_truth = json.loads(open(GT_FP).read())

    descs_by_id = {
        ed['node_id']: ed for ed in ground_truth['results_new']['elem_descriptions']
    }
    cluster_objects = []
    for c_ids in ground_truth['cluster_ids']:
        eds = [descs_by_id[id] for id in c_ids]
        cluster_objects.append(
            Cluster(eds)
        )

    draw_clusters_image2(IMAGE_FP, cluster_objects)
    import pdb; pdb.set_trace()
    elem_descs = ground_truth['results_new']['elem_descriptions']

    ctx = create_screenshot_context(image, imageQ)
    import pdb; pdb.set_trace()
    for i, ed1 in enumerate(elem_descs):
        img_data1 = get_img_data(ed1, ctx)
        for j, ed2 in enumerate(elem_descs):
            if i >= j:
                continue
            img_data2 = get_img_data(ed2, ctx)
            if img_data1['dummy'] or img_data2['dummy']:
                continue
            val1 = _compare_summaries(img_data1, img_data2)
            val2 = _hist_difference(img_data1, img_data2)
            val3 = _compare_structure(img_data1, img_data2)
            val4 = _compare_colours(img_data1, img_data2)
            # print(val1, val2, val3, val4)


if __name__ == '__main__':
    main()
