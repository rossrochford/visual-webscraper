import numpy as np

from util_core.util.content_analysis import is_more_link_text
from util_core.util.string_util import string_distance, string_distance_simple


def _compare_outer_sim(ld1, ld2, context):

    if ld1['parent_tag_name'] != ld2['parent_tag_name'] and ld1['tag_name'] != ld2['tag_name']:
        return 1

    if ld1['parent_outer_html_no_content'] and ld2['parent_outer_html_no_content']:
        max_len = max(
            len(ld1['parent_outer_html_no_content']),
            len(ld2['parent_outer_html_no_content'])
        )
        if max_len > 450:
            min_len = min(
                len(ld1['parent_outer_html_no_content']),
                len(ld2['parent_outer_html_no_content'])
            )
            if max_len / min_len > 3:
                return 1

        parent_outer_sim = string_distance_simple(
            ld1['parent_outer_html_no_content'][:550],
            ld2['parent_outer_html_no_content'][:550]
        )
        if parent_outer_sim < 0.11:
            return 0

    if (ld1['num_tags'] > 2 and ld2['num_tags'] > 2) or (len(ld1['outer_html_no_content']) > 160 and len(ld2['outer_html_no_content']) > 160):
        outer_sim = string_distance(
            ld1['outer_html_no_content'],
            ld2['outer_html_no_content']
        )
        if outer_sim < 0.1:
            return 0
        if outer_sim > 0.85:
            return 1

    return None


'''
def _compare_outer_sim(ld1, ld2, context):

    if ld1['parent_outer_html'] and ld2['parent_outer_html']:
        parent_outer_sim = outer_similarity(ld1['parent_outer_html'], ld2['parent_outer_html'])[0]
        if parent_outer_sim < 0.1:
            return 0

    if (ld1['num_tags'] > 2 and ld2['num_tags'] > 2) or (len(ld1['outer_html_no_content']) > 160 and len(ld2['outer_html_no_content']) > 160):
        outer_sim = outer_similarity(ld1['outer_html'], ld2['outer_html'])[0]
        if outer_sim < 0.1:
            return 0
        if outer_sim > 0.85:
            return 1

    return None
'''

'''
def _compare_img(ed1, ed2, context):

    has_img1 = '<img' in ed1['outer_htmlL'] or 'background-image: url(' in ed1['outer_htmlL']
    has_img2 = '<img' in ed2['outer_htmlL'] or 'background-image: url(' in ed2['outer_htmlL']  # or should we use parent_outer_html?

    if has_img1 and has_img2:
        return 0
    if has_img1 or has_img2:
        return 1

    if ed1['parent_outer_htmlL'] and ed2['parent_outer_htmlL']:
        p_has_img1 = '<img' in ed1['parent_outer_htmlL'] or 'background-image: url(' in ed1['parent_outer_htmlL']
        p_has_img2 = '<img' in ed2['parent_outer_htmlL'] or 'background-image: url(' in ed2['parent_outer_htmlL']

        if p_has_img1 and p_has_img2:
            return 0.25
        if p_has_img1 or p_has_img2:
            return 0.75

    return None
'''


def _compare_img(ed1, ed2, context):
    # note: this misses the case where both elems have a
    # background-img but one has an <img src> which gets precedence
    img_type1, img_type2 = ed1['img_type'], ed2['img_type']
    if img_type1 or img_type2:
        return int(img_type1 != img_type2)

    p_img_type1, p_img_type2 = ed1['parent_img_type'], ed1['parent_img_type']
    if p_img_type1 or p_img_type2:
        return int(p_img_type1 != p_img_type2)

    return None


def _compare_text(ld1, ld2, context):

    text1, text2 = ld1['text'], ld2['text']

    if not (text1 or text2):  # both blank
        return None

    if text1 == text2:
        return 0

    if len(text1) == 0 or len(text2) == 0:
        return 1

    is_more1 = is_more_link_text(ld1['text'])
    is_more2 = is_more_link_text(ld2['text'])

    if is_more1 and is_more2:
        return 0
    if is_more1 or is_more2:
        return 1

    if text1.isdigit() and text2.isdigit():  # todo: do this in ElementDescription and store in ld
        if len(text1) == len(text2):
            return 0
        return 0.15

    date_found1, date_found2 = ld1['text_has_date'], ld2['text_has_date']
    if date_found1 and date_found2:
        if date_found1 == date_found2:
            return 0
        return 0.35
    elif date_found1 or date_found2:
        return 1

    return None


def _compare_start_tag(ld1, ld2, context):

    start_tag1, start_tag2 = ld1['start_tag'], ld2['start_tag']
    p_start_tag1, p_start_tag2 = ld1['parent_start_tag'], ld2['parent_start_tag']

    if p_start_tag1 == p_start_tag2:
        if start_tag1 == start_tag2:
            return 0
        return 0.25
    if start_tag1 == start_tag2 and len(start_tag1) > 24:
        return 0
    return None


FUNCTIONS = [
    _compare_outer_sim,
    _compare_img,
    _compare_text,
    _compare_start_tag
]


def compare_content(ld1, ld2, context):

    signals = [
        func(ld1, ld2, context) for func in FUNCTIONS
    ]
    signals = [val for val in signals if val is not None]

    if not signals:
        return 0.5

    return float(np.mean(signals))


'''
def compare_content(ld1, ld2, context):

    if not (ld1['text'] or ld2['text']):  # both blank
        return 0.5

    if ld1['text'] == ld2['text']:
        return 0

    num_tags1, num_tags2 = ld1['num_tags'], ld2['num_tags']

    if num_tags1 > 2 or num_tags2 > 2:
        ratio = max(num_tags1, num_tags2) / min(num_tags1, num_tags2)
        if ratio > 5:
            return 1
        if ratio > 2 or abs(num_tags1-num_tags2) >= 3:
            return 1
        outer_sim = outer_similarity(ld1['outer_html'], ld2['outer_html'])[0]
        if outer_sim < 0.25:
            import pdb; pdb.set_trace()
            return 0
        if outer_sim > 0.88:
            return 1

    return None
'''
