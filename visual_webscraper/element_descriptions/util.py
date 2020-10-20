
from collections import defaultdict


def calculate_computed_style_weights(link_descriptions):

    num_descs = len(link_descriptions)
    counts = defaultdict(int)
    weights = {}

    for ld in link_descriptions:
        for k, v in ld['all_computed_styles'].items():
            k = '%s___%s' % (k, v)
            counts[k] += 1
    for k_v, count in counts.items():
        weight = (num_descs - count) / num_descs
        weight = max(weight, 0.12)
        weights[k_v] = weight
    return weights


def add_hashes(descriptions):
    hash_counts = {}
    for ld in descriptions:
        hash_str = str(hash(ld['outer_html']))
        hash_counts[hash_str] = hash_counts.get(hash_str, 0) + 1
        if hash_counts[hash_str] > 1:
            hash_str = hash_str + '__' + str(hash_counts[hash_str])
        ld['outer_html_hash'] = hash_str


def add_computed_style_weights(link_descriptions, context):
    weights = context['computed_style_weights']
    for ld in link_descriptions:
        di = {}
        for k_v in ld['all_computed_styles_str']:
            k = k_v.split('___')[0]
            di[k] = weights[k_v]
        ld['computed_style_weights'] = di


def get_spatial_visibility(rect):  # todo: check against page width/height also
    category = None
    if rect['x'] >= 0 and rect['y'] >= 0:
        category = 'IN_PAGE'
    elif rect['x'] == 0 and rect['y'] == 0:
        category = 'AT_ZERO'
    elif rect['x'] < 0 and rect['x'] + rect['width'] <= 0:
        category = 'OUTSIDE_PAGE'
    elif rect['y'] < 0 and rect['y'] + rect['height'] <= 0:
        category = 'OUTSIDE_PAGE'
    elif rect['x'] < 0:
        if rect['x'] + rect['width'] > 2:  # let's ignore 1 and 2
            category = 'OUTSIDE_PAGE_PARTIALLY'
        else:
            category = 'OUTSIDE_PAGE'
    elif rect['y'] < 0:
        if rect['y'] + rect['height'] > 2:
            category = 'OUTSIDE_PAGE_PARTIALLY'
        else:
            category = 'OUTSIDE_PAGE'

    if category is None:
        import pdb; pdb.set_trace()
        category = 'UNKNOWN'

    if rect['width'] == 0 or rect['height'] == 0:
        category = category + '__ZERO_AREA'
    return category
