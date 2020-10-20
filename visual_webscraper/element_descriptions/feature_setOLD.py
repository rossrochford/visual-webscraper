from util_core.util.html_analysis import get_class_str
from util_core.util.url_analysis import is_social_url


STANDARD_FEATURES = [
    'height', 'font-size', 'font-colour',
    'parent_tag_class', 'grandparent_tag_class',
    'xpath_no_nums',
]
FEATURES_INCLUDE_IF_TRUE = [
    'sibling_tags',  # todo: exclude 'a' and only consider true if if has others
    'self_classes',
]
# todo: add 'visibility' attribute if != 'visible'


LOW_PRIORITY_SINGLE = [
    'self_id', 'parent_id', 'grandparent_id',
    'start_tag', 'parent_start_tag',
]

LOW_PRIORITY_LIST = [
    'self_classes',
    'parent_classes',
    'grandparent_classes',
    'parent_other_attrs',
    'self_other_attrs',
]


class FeatureSet(object):

    def __init__(self, ld, context):
        self.ld = ld
        self.context = context

    def _get_additional_features(self):
        features = []
        if self.ld['visibility'] != 'visible':
            features.append('visibility__' + self.ld['visibility'])

        features.append(
            'inner_has_tags__%s' % ('<' in self.ld['inner_html'])
        )

        return features

    def _get_standard_features(self):
        features = [
            key + '__' + str(self.ld[key])
            for key in STANDARD_FEATURES if key in self.ld
        ]
        return features

    def _get_if_true(self):
        features = []
        for key in FEATURES_INCLUDE_IF_TRUE:
            ans = self.ld.get(key)
            if not ans:
                continue
            if key == 'sibling_tags':
                ans = [t for t in ans if t != 'a']
                if not ans:
                    continue
            if key in ('parent_other_attrs', 'self_classes', 'self_other_attrs', 'sibling_tags'):
                features.append(key+'__'+get_class_str(self.ld[key]))
        return features

    def _get_low_priority_single(self):
        features = []
        for key in LOW_PRIORITY_SINGLE:
            val = self.ld.get(key)
            if key.endswith('_id') and not val:
                continue
            features.append(key+'__'+str(val))
        return features

    def _get_low_priority_list(self):
        features = []
        for key in LOW_PRIORITY_LIST:
            li = self.ld.get(key)
            if not li:
                continue
            if type(li) not in (list, tuple):
                import pdb; pdb.set_trace()
            if key == 'self_classes':
                import pdb; pdb.set_trace()
            for item in li:
                features.append(
                    key[:-2]+'__'+str(item)
                )
        return features

    def to_list(self):
        features = self._get_standard_features()
        features.extend(self._get_additional_features())
        features.extend(self._get_if_true())

        features_lowP = self._get_low_priority_single()
        features_lowP.extend(self._get_low_priority_list())

        return features, features_lowP


class LinkFeatureSet(FeatureSet):

    def _get_url_host_feature(self):
        if is_social_url(self.ld['url']):
            url_host = 'url_host__SOCIAL_URL_HOST'
        else:
            url_host = 'url_host__' + self.ld['url_host']
        return url_host

    def _get_standard_features(self):
        features = super(LinkFeatureSet, self)._get_standard_features()
        features.append(
            'url_type__' + self.ld['url_type']
        )
        features.append(self._get_url_host_feature())
        return features

    def _get_low_priority_single(self):
        features = super(LinkFeatureSet, self)._get_low_priority_single()
        for i, f in enumerate(features):
            if f.startswith('start_tag'):
                features[i] = 'start_tag__'+self.ld['start_tag_no_href']
                if features[i] == 'start_tag__<a href="">':  # NOTE: this assumes start_tag was normalised (for example not ending in: href="" >)
                    del features[i]
                    return features  # return here so the iterator doesn't complain
        return features
