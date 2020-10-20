import re

from util_core.util.content_analysis import is_more_link_text
from util_core.util.html_util import (
    get_start_tag, get_tag_names, get_inner, get_tag_name, get_attrs,
    get_text, get_normalised_attrs, remove_html_content, get_tags
)

from webextractor.clustering.comparisons.computed_styles import EXPECTED_COMPUTED_STYLE_KEYS
from webextractor.element_descriptions.util import get_spatial_visibility
from webextractor.element_descriptions.descriptions import get_url_data
from webextractor.selenium_wrapper.preloading import (
    preload_element_data, get_multiple_outer__chunk, AncestorPath,
)


# whether to convert feature_set and all_computed_styles__array to integers
CONVERT_TO_NUMS = True


# r'[day_num_optword] [month_W]'
DAY_NUM_OPTWORD_MONTH = '(?P<day_num>01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|1|2|3|4|5|6|7|8|9)(st|nd|rd|th)? (of )?(?P<month_W>january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)'
# r'[month_W] [day_num_word]'
MONTH_DAY_NUM_WORD = '(?P<month_W>january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec) (?P<day_num>01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|1|2|3|4|5|6|7|8|9)(st|nd|rd|th)'
# r'[month_W] [year_4]
MONTH_YEAR = '(?P<month_W>january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec) (?P<year>2010|2011|2012|2013|2014|2015|2016|2017|2018|2019|2020|2021|2022|2023|2024)'
# r'[time]'
TIME = '((?P<hour_1>00|01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|18|19|20|21|22|23|0|1|2|3|4|5|6|7|8|9)(:|\\.)(?P<minute>(0|1|2|3|4|5)(0|5))\\s?(?P<am_pm_1>a\\.m\\.|p\\.m\\.|am|pm)?|(?P<hour_2>00|01|02|03|04|05|06|07|08|09|10|11|12|1|2|3|4|5|6|7|8|9)\\s?(?P<am_pm_2>a\\.m\\.|p\\.m\\.|am|pm))'
# r'[day_name]'
DAY_NAME = '(?P<day_name>monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|thur|thurs|fri|sat|sun)'

TEXT_DATE_REGEXPS = [
    (DAY_NUM_OPTWORD_MONTH, 'DAY_NUM_OPTWORD_MONTH'),
    (MONTH_DAY_NUM_WORD, 'MONTH_DAY_NUM_WORD'),
    (MONTH_YEAR, 'MONTH_YEAR'),
    (TIME, 'TIME'),
    (DAY_NAME, 'DAY_NAME')
]


def has_date(txt):
    if not txt:
        return None
    for reg, key in TEXT_DATE_REGEXPS:
        if re.search(reg, txt, flags=re.I):
            return key
    return None


def get_img_type(outer_htmlL):
    if '<img' in outer_htmlL:
        return 'IMG'
    elif 'background-image: url(' in outer_htmlL:
        return 'BACKGROUND_IMG'
    # todo: should we include png vs jpg?
    return None


'''
    def class_str(self):

        class_str = self.attrs.get('class', '').strip()
        if not class_str:
            return ''

        classes = []
        for cls in class_str.split(' '):
            cls = cls.lower().strip()
            if cls == 'active':
                continue
            cls = re.sub(r'\d+', '__N__', cls)
            classes.append(cls)
        return str(sorted(classes))

    @cached_property
    def tag_class_str(self):
        return self.tag_name + '__' + self.class_str

'''


def _get_class_attr_str(html_attrs):
    class_str = html_attrs.get('class', '').strip()
    if not class_str:
        return ''
    classes = []
    for cls in class_str.split(' '):
        cls = cls.lower().strip()
        if cls == 'active':
            continue
        cls = re.sub(r'\d+', '__N__', cls)
        classes.append(cls)
    return str(sorted(classes))


def _get_outer_html_data(outer_html):

    outer_htmlL = outer_html.lower()
    inner_html = get_inner(outer_html)

    txt = get_text(outer_html, inner_html)
    outer_no_content = remove_html_content(outer_htmlL, l=False)

    tag_name = get_tag_name(outer_html)
    html_attrs = get_attrs(outer_html)
    class_attr_str = _get_class_attr_str(html_attrs)

    return {
        'outer_html': outer_html,
        'outer_htmlL': outer_htmlL,
        'inner_html': inner_html,
        'outer_html_no_content': outer_no_content,
        'outer_html_no_content_rev': ''.join(reversed(outer_no_content)),
        'text': txt,
        'textL': txt.lower(),
        'text_is_digit': txt.isdigit(),
        'num_tags': round(outer_html.count('<') / 2),
        'text_has_date': has_date(txt) or '',
        'text_is_more_link': is_more_link_text(txt),
        'start_tag': get_start_tag(outer_html, normalise=True),
        'tag_name': tag_name,
        'tags_key': '__'.join(get_tags(outer_html, l=True, exclude_br=True)),
        'tag_class_str': tag_name + '__' + class_attr_str,
        'html_attrs': html_attrs,
        'img_type': get_img_type(outer_htmlL) or '',
        # 'img_url': get_img_url(outer_htmlL, self.page_url_host)  doesn't seem to be used?
    }


def process_outer_html__url(elem_ids, outers, context):

    partial_descs = []
    for i, outer_html in enumerate(outers):
        ed = _get_outer_html_data(outer_html)
        ed['node_id'] = elem_ids[i]
        ed.update(get_url_data(outer_html, context))
        partial_descs.append(ed)

    return partial_descs


def process_ancestor_paths(elem_ids, ancestor_paths):

    partial_descs = []

    for i, path in enumerate(ancestor_paths):
        path = AncestorPath(path)
        parent_outer = path.get(1, 'outer_html') or ''
        parent_outerL = parent_outer.lower() if parent_outer else ''
        ed = {
            'node_id': elem_ids[i],
            'ancestor_path': path,
            'parent_tag_name': path.get(1, 'tag_name') or '',
            'parent_outer_html': parent_outer,
            'parent_outer_htmlL': parent_outerL,
            'parent_outer_html_no_content': remove_html_content(parent_outerL) if parent_outer else '',
            'parent_start_tag': get_start_tag(parent_outer, normalise=True) if parent_outer else '',
            'parent_img_type': (get_img_type(parent_outerL) or '') if parent_outer else ''
        }
        partial_descs.append(ed)

    return partial_descs


def process_xpaths(elem_ids, xpaths):
    partial_descs = []

    for i, xpath in enumerate(xpaths):
        ed = {'xpath': xpath, 'node_id': elem_ids[i]}

        xpath_no_nums = re.sub(r'\[\d{1,2}\]', '', xpath)
        if xpath_no_nums.count('/') < 5:
            ed['xpath_suffix'] = xpath_no_nums
        else:
            ed['xpath_suffix'] = '/'.join(xpath_no_nums.split('/')[-4:])

        partial_descs.append(ed)

    return partial_descs


def _create_desc_from_rect(elem_id, rect):
    area = int(round(rect['height'] * rect['width']))
    rect = {
        'x': int(round(rect['x'])),
        'y': int(round(rect['y'])),
        'height': int(round(rect['height'])),
        'width': int(round(rect['width'])),
        'area': area
    }
    # todo: rect_int, rect_box?
    return {
        'node_id': elem_id,
        'rect': rect,
        'spatial_visibility': get_spatial_visibility(rect)
    }


def process_rects(elem_ids, rects):

    partial_descs = []

    for i, rect in enumerate(rects):
        ed = _create_desc_from_rect(
            elem_ids[i], rect
        )
        partial_descs.append(ed)

    return partial_descs


def _add_computed_style_integers(partial_descs, context):
    computed_style_string_to_num = context['computed_style_string_to_num']

    for ed in partial_descs:
        ed['all_computed_styles__array_int'] = [
            -1 for k in EXPECTED_COMPUTED_STYLE_KEYS
        ]

        for i, cc in enumerate(ed['all_computed_styles__array']):
            if len(cc) == 0:
                ed['all_computed_styles__array_int'][i] = -1
                continue
            key = (i, cc)
            if key not in computed_style_string_to_num:
                computed_style_string_to_num[key] = len(computed_style_string_to_num)
            ed['all_computed_styles__array_int'][i] = computed_style_string_to_num[key]


def process_computed_styles(elem_ids, computed_styles, context):
    partial_descs = []

    for i, cs_data in enumerate(computed_styles):
        ed = {
            'node_id': elem_ids[i],
            'font-size': cs_data['font-size'],
            'font-weight': cs_data['font-weight'],
            'font-colour': cs_data['color'],
            'color': cs_data['color'],
            'cssComputed__visibility': cs_data['visibility'].lower(),
            'cssComputed__display': cs_data['display'].lower(),
            'jquery__is_hidden': not cs_data['is_visible_jquery'],
            # NOTE: 'spatial_visibility' is computed in process_rects()
            # and 'driver__is_displayed' is computed in the main thread
            'all_computed_styles': cs_data['all_computed_styles'],  # used by neural net
        }

        ed['all_computed_styles__array'] = [
            ed['all_computed_styles'].get(k, '')[:100]
            for k in EXPECTED_COMPUTED_STYLE_KEYS
        ]

        partial_descs.append(ed)

    if CONVERT_TO_NUMS:
        #with collection.lock:
        _add_computed_style_integers(partial_descs, context)

    return partial_descs
