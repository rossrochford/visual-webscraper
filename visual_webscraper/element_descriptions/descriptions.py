import re
from urllib.parse import urlparse

import numpy as np

from util_core.util.url_analysis import is_social_url
from util_core.util.urls_util import normalise_href_url, url_host, url_type
from util_core.util.html_util import (
    get_start_tag, get_tag_names, get_inner, get_tag_name,
    get_text, get_normalised_attrs
)
# from selenium_data_extraction.create_data.create_element_descriptions_util import get_spatial_visibility
# from selenium_data_extraction.create_data.create_element_descriptions_util import (
#     find_common_features, calculate_computed_style_weights, add_hashes, add_computed_style_weights,
#     get_spatial_visibility, get_tag_desc, get_ancestor_tag_info, get_ancestor_tag_info_bs4
# )

from webextractor.clustering.comparisons.computed_styles import EXPECTED_COMPUTED_STYLE_KEYS
from webextractor.element_descriptions.util import get_spatial_visibility
from webextractor.element_descriptions.feature_set import create_feature_set
from util_core.util.url_analysis import is_social_url, is_google_calendar_link
from util_core.util.html_analysis import create_outer_summary
from util_core.util.html_util import (
    get_xpath_attrs_condition, get_img_url, remove_html_content, get_href
    # normalise_outer
)

EVENTBRITE_EVENT_REGEX = r'eventbrite\.[a-z\.]{2,6}/e/'
GOOGLE_MAPS_REGEX = r'google\.[a-z\.]{2,6}/maps/'

EXPECTED_CSS_DISPLAY_VALS = (
    'inline', 'block', 'inline-flex', 'flex', 'inline-block', '-webkit-box',
    'table', 'inline-table', 'table-cell', 'list-item'
)


def is_eventbrite_event(u):
    return bool(re.search(EVENTBRITE_EVENT_REGEX, u))


def is_google_map(u):
    if 'maps.google.co' in u:
        return True
    if re.search(GOOGLE_MAPS_REGEX, u) or 'maps.google' in u:  # todo: this is too simple
        return True
    return False


def is_meetup_event(u):
    pass  # todo


ALL_VISIBLE = {'cssComputed__visibility': 'visible', 'jquery__is_hidden': False, 'driver__is_displayed': True, 'spatial_visibility': 'IN_PAGE'}  # 'cssComputed__display': 'block'}


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


def get_url_data(outer_html, context):
    from webextractor.element_descriptions.descriptions import (
        is_eventbrite_event, is_google_calendar_link, is_google_map
    )
    page_url = context['page_url']
    page_url_host = context['page_url_host']
    page_host_base = context['page_host_base']

    url = get_href(outer_html)
    url = normalise_href_url(url, page_url, page_host_base)
    url = (url or '').strip()

    di = {
        'url': url,
        'url_type': url_type(url) or '',
        'url_host': '',
        'url_lower': url.lower(),
    }

    if '..' in url:  # sometimes happens for some reason
        import pdb; pdb.set_trace()
        print()

    if url:

        if url and is_social_url(url):
            di['url_host'] = 'SOCIAL_URL_HOST'
        elif di['url_type'] == 'WEBPAGE':
            di['url_host'] = url_host(url)

        #di['url_no_nums'] = re.sub(r'\d+', 'N', di['url']) if di['url'] else None
        #di['url_no_args'] = url.split('?')[0] if '?' in url else url
        #url_params, url_param_names = _get_url_params(url, page_url_host, di['url_host'])
        #di['url_params'], di['url_param_names'] = url_params, url_param_names
        di['url__is_google_map'] = is_google_map(url)
        di['url__is_eventbrite_event'] = is_eventbrite_event(url)
        di['url__google_calendar'] = is_google_calendar_link(url)
        di['url__is_social'] = is_social_url(url)
        url_no_params = url.split('?')[0].rstrip('/')
        di['url__contains_event'] = 'event' in url and not url_no_params.endswith('events')

    else:
        di.update({
            'url__is_google_map': False,
            'url__is_eventbrite_event': False,
            'url__google_calendar': False,
            'url__is_social': False,
            'url__contains_event': False
        })

    return di


def _get_url_params(url, page_url_host, url_host_val):
    url_params, url_param_names = {}, []

    if url_host_val == page_url_host and '?' in url:
        query = urlparse(url).query.strip().rstrip('&')
        if query:
            if '=' not in query:
                url_params = {query: ''}
                url_param_names = query
            else:
                try:
                    url_params = dict([
                        (s.split('=', 1) if '=' in s else (s, 'NO_EQUALS'))
                        for s in query.split('&') if s
                    ])
                except:
                    import pdb; pdb.set_trace()
                url_param_names = list(sorted(url_params.keys()))
    return url_params, url_param_names


class ElemDescription(object):

    def __init__(self, elem_node, index, context):
        self.elem_node = elem_node
        self.context = context
        self.index = index
        self.page_url_host = context['page_url_host']
        #self.ancestor_path = None

    @classmethod
    def create(cls, elem_node, index, context):
        e = cls(elem_node, index, context)
        if elem_node.tag_name == 'a':
            e.__class__ = LinkElemDescription
        return e

    def _get_computed_styles(self):
        styles = self.elem_node.all_computed_styles
        styles_array = np.array([
            # clip at 100 characters
            styles.get(k, '')[:100] for k in EXPECTED_COMPUTED_STYLE_KEYS
        ])
        return {
            'all_computed_styles': styles,
            'all_computed_styles_str': [
                k + '___' + v for (k, v) in styles.items()
            ],
            'all_computed_styles__array': styles_array
        }

    def _get_html_content(self):

        outerL = self.elem_node.outer_htmlL
        txt = self.elem_node.text

        def has_date():
            if not txt:
                return None
            for reg, key in TEXT_DATE_REGEXPS:
                if re.search(reg, txt, flags=re.I):
                    return key
            return None

        di = {
            'outer_html': self.elem_node.outer_html,
            'outer_htmlL': self.elem_node.outer_htmlL,
            #'outer_html_normalised': normalise_outer(self.elem_node.outer_htmlL, l=False),
            'inner_html': get_inner(self.elem_node.outer_html),
            #'outer_desc': get_tag_desc(self.elem_node.outer_html, prepare=True),
            'outer_html_no_content': remove_html_content(outerL, l=False),
            'text': txt,  # todo: can we do something to minimise calls to this in preload script?
            'num_tags': round(self.elem_node.outer_html.count('<') / 2),  # todo: move this to another method?
        }
        if di['text'] == "What's On" and 'visually-hidden' in di['outer_html']:
            import pdb; pdb.set_trace()
            print()

        di['text_has_date'] = has_date()

        return di

    def _get_self_tag_info(self):
        outer = self.elem_node.outer_html
        parent_elem = self.elem_node.ancestor_path.get(1, 'elem')
        parent_outer = parent_elem.outer_html if parent_elem else None
        parent_outerL = parent_outer.lower() if parent_outer else None

        return {
            # todo: we should batch-load outer_html for nodes in parent path
            'parent_tag_name': get_tag_name(parent_outerL) if parent_outerL else None,
            'parent_outer_html': parent_outer,
            'parent_outer_htmlL': parent_outerL if parent_elem else None,
            'parent_outer_html_no_content': remove_html_content(parent_outerL, l=False) if parent_elem else None,
            #'parent_outer_html_normalised': normalise_outer(parent_outerL, l=False) if parent_elem else None,
            'parent_start_tag': get_start_tag(parent_outer, normalise=True) if parent_elem else None,
            'start_tag': get_start_tag(outer, normalise=True),
            'tag_name': self.elem_node.tag_name,
            'tags_key': self.elem_node.get_tags_key()
        }

    def _get_visibility_info(self):
        # is_displayed__full = True
        # is_displayed__fast = True
        # if self.elem_node.get_is_visible_fast() is False:
        #     is_displayed__full = False
        #     is_displayed__fast = False
        # elif self.elem_node.driver_elem.is_displayed() is False:  # bypassing wrapper method here for certainty when gather ground truth
        #     is_displayed__full = False

        # if is_displayed__fast is False or is_displayed__full is False:
        #     import pdb; pdb.set_trace()

        if self.elem_node.driver_elem.is_displayed() is False and self.elem_node.is_displayed():
            print('warning: is_displayed() discrepancy detection disabled')
            #import pdb; pdb.set_trace()

        di = {
            'spatial_visibility': get_spatial_visibility(self.elem_node.rect),

            'driver__is_displayed': self.elem_node.is_displayed(),
            'cssComputed__display': self.elem_node.value_of_css_property('display'),
            'cssComputed__visibility': self.elem_node.value_of_css_property('visibility'),  # usually 'visible'
            'jquery__is_hidden': self.elem_node.is_hidden_jquery,

            #'is_displayed__fast': is_displayed__fast,
            #'is_displayed__full': is_displayed__full,

            # also: self.elem_node.is_displayed and elem_node.is_visible but I think
            # these may be redundant or not worth the cost
        }
        #print(self.elem_node.value_of_css_property('display'))
        #if di['jquery__is_hidden'] != (not di['driver__is_displayed']):
        #    import pdb; pdb.set_trace()  # if this continues to never catch, we can stop using is_displayed()

        di['visibility__ALL_VISIBLE'] = True
        for key, visible_val in ALL_VISIBLE.items():
            if di[key] != visible_val:
                di['visibility__ALL_VISIBLE'] = False
                break
        if di['visibility__ALL_VISIBLE'] and di['cssComputed__display'] not in EXPECTED_CSS_DISPLAY_VALS:
            print('cssComputed__display___'+di['cssComputed__display'])
            import pdb; pdb.set_trace()
            di['visibility__ALL_VISIBLE'] = False

        return di

    def _get_img_info(self, ed):

        img_type = None
        if '<img' in ed['outer_htmlL']:
            img_type = 'IMG'
        elif 'background-image: url(' in ed['outer_htmlL']:
            img_type = 'BACKGROUND_IMG'

        p_img_type = None
        if '<img' in (ed['parent_outer_htmlL'] or ''):
            p_img_type = 'IMG'
        elif 'background-image: url(' in (ed['parent_outer_htmlL'] or ''):
            p_img_type = 'BACKGROUND_IMG'

        img_url = get_img_url(ed['outer_htmlL'], self.page_url_host)

        return {
            'img_type': img_type,
            'parent_img_type': p_img_type,
            'img_url': img_url
        }

    def _get_xpaths(self):

        # todo: can probably remove most of this stuff

        xpath = self.elem_node.xpath  # xpath_soup(self.bs4_elem)
        di = {'xpath': xpath}
        # for i, num in enumerate(re.findall(r'\[\d{1,2}\]', xpath)):
        #     xpath = xpath.replace(num, '', 1)  # probably not the most efficient way

        di['xpath_no_nums'] = re.sub(r'\[\d{1,2}\]', '', xpath)

        if di['xpath_no_nums'].count('/') < 5:
            di['xpath_suffix'] = di['xpath_no_nums']
        else:
            di['xpath_suffix'] = '/'.join(di['xpath_no_nums'].split('/')[-4:])

        attrs = self.elem_node.attrs
        if attrs:
            for k, v in attrs.items():
                if type(v) is list:
                    attrs[k] = ' '.join(v)
            di['xpath_w_attrs'] = xpath.rstrip('/') + get_xpath_attrs_condition(
                attrs, remove_href=True
            )
            di['xpath_no_nums_w_attrs'] = di['xpath_no_nums'].rstrip('/') + get_xpath_attrs_condition(
                attrs, remove_href=True
            )
        else:
            di['xpath_w_attrs'] = di['xpath']
            di['xpath_no_nums_w_attrs'] = di['xpath_no_nums']

        return di

    '''
    def _get_feature_sets(self):
        features_new, features_lowP_new = FeatureSet(self.ld, {}).to_list()
        di = {
            'feature_set_new': features_new,
            'feature_set_low_priority_new': features_lowP_new
        }
        return di'''

    def _get_font_info(self):
        return {
            'font-size': self.elem_node.font_size,
            'font-colour': self.elem_node.font_colour,
            'font-weight': self.elem_node.font_weight,
        }

    def _get_rect_info(self):
        return self.elem_node.rect_info

    def _get_url_params(self, url_host_val):

        url_params, url_param_names = {}, []
        url = self.elem_node.url

        if url_host_val == self.page_url_host and '?' in url:
            query = urlparse(url).query.strip().rstrip('&')
            if query:
                if '=' not in query:
                    url_params = {query: ''}
                    url_param_names = query
                else:
                    try:
                        url_params = dict([
                            (s.split('=', 1) if '=' in s else (s, 'NO_EQUALS'))
                            for s in query.split('&') if s
                        ])
                    except:
                        import pdb; pdb.set_trace()
                    url_param_names = list(sorted(url_params.keys()))
        return url_params, url_param_names

    def _get_url_info(self):
        return get_url_data(self.elem_node.outer_html, self.context)

    def to_dict(self):
        methods = [
            self._get_computed_styles,
            self._get_self_tag_info,
            self._get_visibility_info, self._get_html_content,
            self._get_xpaths,
            self._get_font_info, self._get_rect_info,
        ]
        if self.elem_node.tag_name == 'a':
            methods.append(self._get_url_info)

        di = {}
        for meth in methods:
            di.update(meth())

        di['feature_set'] = create_feature_set(self.elem_node, di)
        di['node_id'] = self.elem_node.id
        di['index'] = self.index

        di.update(self._get_img_info(di))

        return di


class LinkElemDescription(ElemDescription):
    pass
