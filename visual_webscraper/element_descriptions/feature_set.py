import re

from util_core.util.url_analysis import is_social_url

FEATURES = [

    'height',
    'font-size', 'font-colour',  'font-weight',
    'xpath_suffix',
    'driver__is_displayed',
    'cssComputed__display',

    'ancestor0__classes',
    'ancestor0__attrs',

    'ancestor1__tag_class',
    'ancestor1__classes',
    'ancestor1__attrs',

    'ancestor2__tag_class',
    'ancestor2__classes',
    'ancestor2__attrs',

    'url_host',
    'url_type',
]


def get_ancestor_featureset_values(ed, ancestor_path, feature_key):

    ancestor, feature_key2 = feature_key.split('__')  # 2 underscores
    ancestor = int(ancestor[8:])

    elem = ancestor_path.get(ancestor, 'elem')

    if elem is None:
        return []

    if feature_key2 == 'classes':
        classes = ed['html_attrs'].get('class', '').strip()
        if not classes:
            return []

        features = []
        for cls in classes.split(' '):
            cls = cls.lower().strip()
            if cls == 'active' or not cls:
                continue  # ignore any class 'active'
            cls = re.sub(r'\d+', '__N__', cls)
            features.append(
                feature_key + '___' + cls  # 3 underscores
            )
        return features

    if feature_key2 == 'tag_class':
        return [feature_key + '___' + ed['tag_class_str']]

    if feature_key2 == 'attrs':
        features = []
        for key, val in ed['html_attrs'].items():
            if key == 'href':
                continue
            features.append(  # 3 underscores, 2 underscores
                feature_key + '___' + key + '__' + str(val)
            )
        return features

    import pdb; pdb.set_trace()
    print('should never get here')


def create_feature_set(elem, ed):
    return _create_feature_set(elem.ancestor_path, ed)


def create_feature_set2(ed):
    return _create_feature_set(ed['ancestor_path'], ed)


def _create_feature_set(ancestor_path, ld):

    features = []

    for feature_key in FEATURES:
        if feature_key.startswith('ancestor'):
            features.extend(
                get_ancestor_featureset_values(ld, ancestor_path, feature_key)
            )
            continue

        if feature_key == 'height':
            features.append(
                feature_key + '___' + str(ld['rect']['height'])
            )
            continue

        if feature_key not in ld:
            if 'url' not in feature_key:
                print('ERROR: missing feature key: '+feature_key)
            continue

        if feature_key == 'url_host':
            if ld.get('url'):
                host = 'SOCIAL_HOST' if is_social_url(ld['url']) else ld['url_host']
                if host is None:
                    continue
                features.append(
                    feature_key + '___' + host
                )
            continue

        if feature_key == 'driver__is_displayed' and ld[feature_key] is True:
            continue

        features.append(  # (3 underscores)
            feature_key + '___' + str(ld[feature_key])
        )

    return features


'''

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


'''