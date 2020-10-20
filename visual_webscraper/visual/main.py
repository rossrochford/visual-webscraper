from PIL import Image

from webextractor.pipeline_new.util import SimDict
from webextractor.visual.compare import visually_similar_NEW
from webextractor.visual.extract import create_screenshot_context, get_img_data
from webextractor.visual.quantize import QuantizedScreenshot


# todo: consider instead using: pyvips

def get_visual_similarities(elem_descriptions, screenshot_data, relevant_comparisons=None, key_type=str):

    assert key_type in (str, tuple)

    img = Image.open(screenshot_data['screenshot_fp'])
    imgQ = QuantizedScreenshot.create(
        screenshot_data['screenshotQ_fp'], quantize=False
    )

    ctx = create_screenshot_context(img, imgQ)

    img_datas = []
    for ed in elem_descriptions:
        img_datas.append(
            get_img_data(ed, ctx)
        )

    if key_type is tuple:
        sim_vals_by_id = SimDict()
    else:
        sim_vals_by_id = {}

    sim_vals_list = []

    for i, img_data1 in enumerate(img_datas):
        id1 = elem_descriptions[i]['node_id']
        for j, img_data2 in enumerate(img_datas):
            if i >= j:
                continue
            id2 = elem_descriptions[j]['node_id']

            if key_type is str:
                key = id1 + '__' + id2
            else:
                key = (id1, id2)

            if relevant_comparisons:
                if (id1, id2) not in relevant_comparisons and (id2, id2) not in relevant_comparisons:
                    sim_vals_by_id[key] = 0.5
                    continue

            sim_vals_by_id[key] = visually_similar_NEW(img_data1, img_data2)
            sim_vals_list.append(sim_vals_by_id[key])

    return sim_vals_by_id, sim_vals_list
