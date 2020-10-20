import uuid

import numpy as np
from sklearn.cluster import DBSCAN, AffinityPropagation
from util_core.util.vuejs import create_vue_elem_dict

# dbscan parameters
EPS = 0.407
MIN_SAMPLES = 2


class Cluster(object):

    def __init__(self, lds):
        self.lds = lds
        self.uid = uuid.uuid4().hex

    @property
    def length(self):
        return len(self.lds)

    def sort(self, key=None):
        self.lds.sort(key=key)

    def get_urls(self, page_url=None):
        urls = [ld['url'] for ld in self.lds if ld['url']]
        if page_url:
            host = url_host(page_url)
            urls = [u for u in urls if host in u]
        return urls

    @property
    def urls_key(self):
        urls = self.get_urls()
        urls = [u for u in set(urls)]
        urls.sort()
        return tuple(urls)

    @property
    def node_ids(self):
        return [ld['node_id'] for ld in self.lds]

    @property
    def text_key(self):
        texts = [ld['text'] for ld in self.lds if ld['text']]
        if not texts:
            return None
        return set(texts)

    @property
    def avg_area(self):
        return np.mean([
            ed['rect']['area'] for ed in self.lds
        ])

    @property
    def is_displayed(self):
        # False is ALL elements are invisible
        for ld in self.lds:
            if ld['driver__is_displayed']:
                return True
        return False

    def is_equivalent(self, other):
        return set(self.get_urls()) == set(other.get_urls())

    def is_visible(self):
        return all(ld['driver__is_displayed'] for ld in self.lds)

    def get_vue_dicts(self):
        return [create_vue_elem_dict(ed) for ed in self.lds]

    def get_avg_sim_to(self, ed, sim_func, context):
        return np.mean([
            sim_func(ed2, ed, context) for ed2
            in self.lds if ed2['node_id'] != ed['node_id']
        ])

    '''
    old methods/properties from clustering_analysis.create_data.core_hl_new.Cluster:
    def avg_area(self):
    def avg_max_height_or_width(self):
    def is_nav_cluster(self, nav_elem_ids):
    def get_xpath_selector(self, driver):
    def get_start_tag_selectors(self, driver):
    def get_outer_sim_selector(self, all_link_descriptions):
    def get_url_selector(self, all_link_descriptions, page_url):
    def find_selectors(self, driver, all_link_descriptions):
    def num_social_event_urls(self):
    def get_rank(self, html_data, nav_elem_ids, score_cache, page_url):
    def detect_split(self, link_descriptions, sim_matrix):
    def detect_outlier(self, link_descriptions, sim_matrix):
    '''

'''
def get_clusters_dbscan(sim_matrix, link_descriptions, eps=EPS, min_samples=MIN_SAMPLES, fix_triangles=False, reduce_noise=False):

    if fix_triangles:
        from clustering_data_explore.util_core.util.matrix_util import fix_triangles as fix_tri
        fix_tri(sim_matrix)

    # preprocess sim_matrix
    print('warning: commented out reduce_noise() and set_hard_boundaries()')
    if reduce_noise:
        sim_matrix = _reduce_noise(sim_matrix)
    #sim_matrix = reduce_noise(sim_matrix)
    #set_hard_boundaries(link_descriptions, sim_matrix)

    db = DBSCAN(metric='precomputed', eps=eps, min_samples=min_samples).fit(sim_matrix)
    labels = db.labels_

'''


def get_clusters_affinity_propagation(sim_matrix, elem_descriptions):
    db = AffinityPropagation(affinity='precomputed').fit(sim_matrix)
    labels = db.labels_
    return _get_clusters_from_labels(labels, elem_descriptions)


def get_clusters_dbscan(sim_matrix, elem_descriptions, eps=EPS, min_samples=MIN_SAMPLES):

    db = DBSCAN(metric='precomputed', eps=eps, min_samples=min_samples).fit(sim_matrix)
    labels = db.labels_
    return _get_clusters_from_labels(labels, elem_descriptions)


def _get_clusters_from_labels(labels, elem_descriptions):

    def _get_from_labels(labels):
        clusters = {}
        unclassified = []
        for i, label in enumerate(labels):
            if label == -1:
                unclassified.append(elem_descriptions[i])
                continue
            clusters[label] = clusters.get(label, []) + [elem_descriptions[i]]
        return clusters, unclassified

    clusters, _ = _get_from_labels(labels)

    all = []
    for c in clusters.values():
        for ld in c:
            all.append(ld)
    for ld in _:
        all.append(ld)

    clusters = [v for v in clusters.values()]
    clusters.sort(key=lambda c: len(c), reverse=True)

    cluster_objects = [Cluster(ld_list) for ld_list in clusters]
    cluster_ids, cluster_ids__flat = [], []
    for curr_cluster in clusters:
        cluster_ids.append([ld['node_id'] for ld in curr_cluster])
        cluster_ids__flat.extend([ld['node_id'] for ld in curr_cluster])

    leftover_ids = [
        ld['node_id'] for ld in elem_descriptions
        if ld['node_id'] not in cluster_ids__flat
    ]
    '''
    #experimenting with splitting clusters by lowest common ancestor:
    from selenium_data_explore.create_data.cluster_refine import split_by_lca__bs4
    elem_descriptions_by_id = {ld['node_id']: ld for ld in elem_descriptions}
    for cluster in cluster_ids[:4]:
        if len(cluster) < 4:
            continue
        bs4_elems = [
            elem_descriptions_by_id[id]['bs4_elem'] for id in cluster
        ]

        sections, _ = split_by_lca__bs4(bs4_elems)
        if sections:
            import pdb; pdb.set_trace()
    '''

    return cluster_objects, cluster_ids, leftover_ids