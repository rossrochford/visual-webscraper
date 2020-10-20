from collections import defaultdict
import random
import time

from util_core.util.urls_util import url_host

from webextractor.selenium_wrapper.main import FirefoxDriverWrapper
import json
import os
import numpy as np

from multiprocessing import Pool

# from clustering_data_explore.util.db_scan import get_clusters_dbscan  # todo: move to webextractor
from webextractor.clustering.comparisons.area_similarity import areas_similar
from webextractor.clustering.comparisons.area_alignment import area_alignment_simple
from webextractor.clustering.comparisons.euclidean_distance import (
    adjusted_euclidean_distance, standard_euclidean_distance
)
from webextractor.clustering.comparisons.computed_styles import (
    compare_computed_styles, compare_computed_styles_jaccard
)
from webextractor.clustering.comparisons.featureset_overlap import featureset_overlap
from webextractor.clustering.comparisons.content import compare_content
from webextractor.clustering.comparisons.is_visible import compare_visibility
from webextractor.clustering.comparisons.spatial_alignment import spatially_aligned
from webextractor.clustering.comparisons.url_similarity import url_similarity
from webextractor.clustering.comparisons.visual_similarity import visually_similar
from webextractor.clustering.ground_truth.create import CreateGroundTruth
from webextractor.selenium_wrapper.elements import LinkWebElementWrapper
from webextractor.selenium_wrapper.cache import ElementCache
from webextractor.selenium_wrapper.preloading import preload_element_data
from webextractor.element_descriptions.descriptions import ElemDescription
from webextractor.process_controller_util.util import create_context
from webextractor.visual.util import ImageRect
from util_core.util.navigation_finding import NavTask
from util_core.util.urls_util import url_host, url_base
from util_core.util.file_util import get_files_in_dir


COMPARISON_FUNCTIONS = [
    adjusted_euclidean_distance,
    area_alignment_simple,
    areas_similar,
    compare_computed_styles,
    compare_computed_styles_jaccard,
    compare_content,
    #compare_navigation_status,
    compare_visibility,
    featureset_overlap,
    spatially_aligned,
    standard_euclidean_distance,
    url_similarity,
    visually_similar
]


def get_distances(link_descriptions, func, context):

    results = {}

    for i, ld1 in enumerate(link_descriptions):
        id1 = ld1['node_id']
        for j, ld2 in enumerate(link_descriptions):
            if i >= j:
                continue
            id2 = ld2['node_id']
            dist = func(ld1, ld2, context)
            results['%s__%s' % (id1, id2)] = dist
            results['%s__%s' % (id2, id1)] = dist
    return results


def do_old_clustering(url):

    from process_controller_util.util import create_context
    from process_controller_util.scrape_webpage import RunKerasClustering
    from visual_matrix_new.image_rect import ImageRect
    from util_core.util.group_analysis import find_url_patterns, find_repeated_text, find_repeated_combo_features
    # from selenium_wrapper.selenium_driver_new import FirefoxDriverWrapper as FirefoxDriverWrapperOld
    from clustering_data_explore.util.db_scan import get_clusters_dbscan  # todo: move to webextractor

    models = [None, None, None, None]
    self = RunKerasClustering(models, -1)
    self.url = url  # hack because we're calling create_driver() before start()
    self.driver = self.create_driver(confirm_height=False)
    link_elems = self.driver.link_elements

    self.start(url=url, initialise_state=False, link_elems=link_elems, driver=self.driver)
    driver = self.driver  # shadow variable in __main__ block below

    sim_matrix_NN = self.sim_matrixNN_L  # todo: we should also save the non-NN sim_matrix
    sim_matrix_NN_by_id = self.sim_matrixNN_L_by_id
    sim_matrix_noNN = self.sim_matrix_noNN_L

    cluster_objects, _ = get_clusters_dbscan(
        sim_matrix_NN, self.link_descriptions, eps=0.407
    )

    matrix_results = self.matrix_results_L

    matrix_results_by_id = {}
    for i, ed1 in enumerate(self.link_descriptions):
        id1 = ed1['node_id']
        for j, ed2 in enumerate(self.link_descriptions):
            if i >= j:
                continue
            id2 = ed2['node_id']
            if i != ed1['index'] or j != ed2['index']:
                import pdb; pdb.set_trace()
            for key in matrix_results.keys():
                val = matrix_results[key][0][i][j]
                if key not in matrix_results_by_id:
                    matrix_results_by_id[key] = {}
                matrix_results_by_id[key]['%s__%s' % (id1, id2)] = val
                matrix_results_by_id[key]['%s__%s' % (id2, id1)] = val

    result_data = {
        'elem_descriptions': self.link_descriptions,
        'clusters': cluster_objects,
        'sim_matrix_NN': sim_matrix_NN,
        'sim_matrix_NN_by_id': sim_matrix_NN_by_id,
        'sim_matrix_noNN': sim_matrix_noNN,
        'matrix_results': matrix_results_by_id,
        'context': self.context,
        'are_links': True
    }

    link_elems_D = [e.driver_elem for e in link_elems]

    return driver, link_elems_D, result_data


def get_computed_style_weights(elem_descriptions):

    counts = defaultdict(int)
    for ed in elem_descriptions:
        for key, val in ed['all_computed_styles'].items():
            counts[(key, val)] += 1
    coefficients = {}
    for key_val, count in counts.items():
        coefficients[key_val] = count / len(elem_descriptions)
    return coefficients


def do_new_clustering(driver):

    # driver = FirefoxDriverWrapper()
    #driver.initialise_for_clustering(url)

    #time.sleep(0.5)
    MULTI = False
    links = driver.get_link_elements()  # driver.find_elements_by_xpath('//a')

    #preload_element_data(driver, links)

    nav_task = NavTask(
        links, url, driver.page_source
    )

    context = create_context(driver, url, get_screenshot=True)

    # todo: put this in a function
    elem_descriptions = [
        ElemDescription(e, i, context).to_dict()  # todo: should use create() right? this means we also need to preload outers beforehand
        for (i, e) in enumerate(links)
    ]
    context['computed_style_weights'] = get_computed_style_weights(elem_descriptions)
    img_rect_lds = []
    for ed in elem_descriptions:
        img_rect_lds.append({
            'img_rect': ImageRect(ed['rect'], context), 'node_id': ed['node_id'],
            'driver__is_displayed': ed['driver__is_displayed']
        })

    matrix_results = {}
    if MULTI:
        pool = Pool(processes=6)
        for func in COMPARISON_FUNCTIONS:
            if func.__name__ in ('visually_similar', 'compare_navigation_status'):
                continue
            matrix_results[func.__name__] = pool.apply_async(
                get_distances, (elem_descriptions, func, context)
            )

        matrix_results['visually_similar'] = get_distances(
            img_rect_lds, visually_similar, context
        )
        for func_name, result in matrix_results.items():
            if func_name != 'visually_similar':
                matrix_results[func_name] = result.get()

        # context['nav_elem_ids'] = [e.id for e in nav_task.get()]
        # matrix_results['compare_navigation_status'] = get_distances(
        #     elem_descriptions, compare_navigation_status, context
        # )
    else:
        for func in COMPARISON_FUNCTIONS:
            if func.__name__ == 'visually_similar':
                matrix_results['visually_similar'] = get_distances(
                    img_rect_lds, visually_similar, context
                )
                continue
            # if func.__name__ == 'compare_navigation_status':
            #     context['nav_elem_ids'] = [e.id for e in nav_task.get()]

            matrix_results[func.__name__] = get_distances(
                elem_descriptions, func, context
            )

    '''
    FUNCTION_NAMES = sorted(matrix_results.keys())  # sort for consistency
    
    sim_matrix = np.zeros((len(elem_descriptions), len(elem_descriptions)))
    for i, ld1 in enumerate(elem_descriptions):
        id1 = ld1['node_id']
        for j, ld2 in enumerate(elem_descriptions):
            if i >= j:
                continue
            id2 = ld2['node_id']

            distances = [
                matrix_results[func_name]['%s__%s' % (id1, id2)]
                for func_name in FUNCTION_NAMES
            ]
            distances = [val for val in distances if abs(0.5 - val) > 0.04]
            dist = np.mean(distances)
            sim_matrix[i][j] = dist
            sim_matrix[j][i] = dist

    cluster_objects, _ = get_clusters_dbscan(
        sim_matrix, elem_descriptions, eps=0.407
    )
    '''

    result_data = {
        'elem_descriptions': elem_descriptions,
        #'clusters': cluster_objects,
        #'sim_matrix_NN': sim_matrix_NN,
        # 'sim_matrix_noNN': sim_matrix,
        'matrix_results': matrix_results,
        'context': context,
        'are_links': True
    }

    #from util_core.util.system import total_size
    #print(total_size(matrix_results)/1024)

    return result_data


def create_ground_truth(url):

    from util_core.util.draw import draw_clusters_on_driver

    driverOLD, link_elems_D, result_dataOLD = do_old_clustering(url)

    driverNEW = FirefoxDriverWrapper(driver=driverOLD.d)
    # normally set in driver.get()
    driverNEW.url = url
    driverNEW.page_host_base = url_base(url)
    # normally called in initialise_for_clustering:
    driverNEW.get_screenshot_data()

    elems_new = []
    for elem_D in link_elems_D:
        elems_new.append(
            LinkWebElementWrapper(elem_D, driverNEW)
        )

    #elems_old_by_id = {e.id: e for e in driverOLD.elem_cache.driver_xpath_cache['//a']}
    elems_new = []
    for ld in result_dataOLD['elem_descriptions']:
        e = driverOLD.elem_cache.elems_cache[ld['node_id']]
        if e.id != ld['node_id']:
            import pdb; pdb.set_trace()
        elems_new.append(LinkWebElementWrapper(e.driver_elem, driverNEW))
    # elems_new = [
    #     LinkWebElementWrapper(e.driver_elem, driverNEW) for e in elems_old
    # ]
    for i, e in enumerate(elems_new):
        e.index = i  # todo: check that indexes are set properly in result_dataOLD['elem_descriptions'] also
        eOLD = driverOLD.elem_cache.elems_cache[e.id]

        e.attr_cache = eOLD.attr_cache

        e.css_prop_cache = eOLD.css_prop_cache
        e.cached_rect = eOLD.cached_rect
        e.first_text_child = eOLD.first_text_child
        e.all_computed_styles = eOLD.all_computed_styles
        e.cached__is_displayed = eOLD.cached_is_displayed
        e.is_hidden_jquery = eOLD.is_hidden_jquery

    driverNEW.elem_cache = ElementCache(driverNEW)
    driverNEW.elem_cache.driver_xpath_cache['//a'] = elems_new

    preload_element_data(driverNEW, elems_new, items=('xpath', 'ancestor_path',))

    driverNEW.link_elems_cached = elems_new

    result_dataNEW = do_new_clustering(driverNEW)

    '''
    from collections import defaultdict
    counts = defaultdict(int)
    for tup in driverOLD.lock.log:
        counts[tup[0]] += 1
    counts2 = defaultdict(int)
    for tup in driverNEW.lock.log:
        counts2[tup[0]] += 1
    import pdb;  pdb.set_trace()'''

    draw_clusters_on_driver(driverOLD, result_dataOLD['clusters'])

    # todo: get link_descriptions using new class but with the same (old) driver object? (or instantiate new instance of new driver that points to selenium object and populate the cache)
    gt = CreateGroundTruth(
        driverNEW, url, result_dataOLD, result_dataNEW
        # driverNEW, self.link_descriptions, cluster_objects,
        # self.matrix_results_L, sim_matrix, self.context, True
    )
    gt.start()


def create_historgram(results, figure_fp):
    import pylab
    import matplotlib.pyplot as plt

    mu, sigma = 100, 15
    #x = mu + sigma * np.random.randn(10000)
    x = results

    #x = mu + sigma * np.random.randn(10000)
    #x = [v/125 for v in x]

    # the histogram of the data
    n, bins, patches = plt.hist(x, 30, normed=1, facecolor='green', alpha=0.75)

    # Show the plot
    pylab.grid(True)
    pylab.xticks(rotation=45)

    plt.savefig(figure_fp)

    #pylab.show()
    #print(results)


MATRIX_RESULTS_NAMES = [
    # maps from old names to new names
    ('adjusted_euclidean_distance', 'adjusted_euclidean_distance'),
    ('areas_similar', 'areas_similar'),
    ('compare_content', 'compare_content'),
    ('spatially_aligned', 'spatially_aligned'),
    ('visually_similar', 'visually_similar'),
    ('compare_navigation_status', 'compare_navigation_status'),
    ('compare_computed_styles', 'compare_computed_styles'),

    ('urls_similar', 'url_similarity'),
    ('get_feature_overlap', 'featureset_overlap'),
    ('visibility_similar', 'compare_visibility')
]

DISPLAY_ATTRS1 = [
    'is_hidden_jquery',
    'spatial_visibility',
    'visibility',
]

DISPLAY_ATTRS2 = [
    'cssComputed__visibility',
    'jquery__is_hidden',
    'cssComputed__display',
    'driver__is_displayed',
    'spatial_visibility',
    'visibility__ALL_VISIBLE',
]


def generate_sim_measurement_report():
    from PIL import Image
    from webextractor.visual.quantize import QuantizedScreenshot
    from webextractor.clustering.comparisons.visual_similarity import visually_similar

    graphs_match = {}
    graphs_no_match = {}

    correlations = defaultdict(list)
    covariances = defaultdict(list)
    discrepancies = defaultdict(list)

    for fp in get_files_in_dir('/home/ross/code/events_project/webextractor/webextractor/clustering/ground_truth/data/cluster_data'):
        if not fp.endswith('.json'):
            continue

        di = json.loads(open(fp).read())
        uid = fp.split('/')[-1].rstrip('.json')

        context = di['context_new']
        context['screenshot_obj'] = Image.open(context['screenshot_fp'])
        context['screenshotQ_obj'] = QuantizedScreenshot.create(
            context['screenshotQ_fp'], quantize=False
        )

        cc_keys = [k for k in context['computed_style_weights'].keys()]
        for key in cc_keys:
            val = context['computed_style_weights'].pop(key)
            key_tup = tuple(key.split('__'))
            context['computed_style_weights'][key_tup] = val

        graphs_match[uid] = defaultdict(list)
        graphs_no_match[uid] = defaultdict(list)

        ids = [ld['node_id'] for ld in di['results_new']['elem_descriptions']]
        elem_descriptions_by_id = {
            ed['node_id']: ed for ed in di['results_new']['elem_descriptions']
        }

        sim_matrixOLD_noNN = di['results_old']['sim_matrix_noNN']
        sim_matrixOLD_NN = di['results_old']['sim_matrix_NN']
        sim_matrixNEW_noNN = di['results_new']['sim_matrix_noNN']

        for func_name1, func_name2 in MATRIX_RESULTS_NAMES:
            if func_name1 not in di['results_old']['matrix_results'] or func_name2 not in di['results_new']['matrix_results']:
                import pdb; pdb.set_trace()

            for cluster in di['cluster_ids']:
                for id1 in cluster:
                    index1 = ids.index(id1)
                    if index1 != elem_descriptions_by_id[id1]['index']:
                        import pdb; pdb.set_trace()
                    for id2 in cluster:
                        if id1 == id2:
                            continue
                        index2 = ids.index(id2)

                        res1 = di['results_old']['matrix_results'][func_name1]['%s__%s' % (id1, id2)]
                        res2 = di['results_new']['matrix_results'][func_name2]['%s__%s' % (id1, id2)]

                        graphs_match[uid][func_name1].append(res1)
                        graphs_match[uid][func_name1 + '_new'].append(res2)
                        graphs_match[uid]['total_similiarity1'].append(sim_matrixOLD_noNN[index1][index2])
                        graphs_match[uid]['total_similiarity2'].append(sim_matrixOLD_NN[index1][index2])
                        graphs_match[uid]['total_similiarity3'].append(sim_matrixNEW_noNN[index1][index2])

                        correlations[func_name1].append([res1, res2])
                        covariances[func_name1].append([res1, res2])
                        disc = 1 if abs(res1-res2) > 0.25 else 0
                        discrepancies[func_name1].append(disc)

            for i, cluster1 in enumerate(di['cluster_ids']):
                for j, cluster2 in enumerate(di['cluster_ids']):
                    if i == j:
                        continue
                    for id1 in cluster1:
                        index1 = ids.index(id1)
                        for id2 in cluster2:
                            res1 = di['results_old']['matrix_results'][func_name1]['%s__%s' % (id1, id2)]
                            res2 = di['results_new']['matrix_results'][func_name2]['%s__%s' % (id1, id2)]
                            index2 = ids.index(id2)

                            graphs_no_match[uid][func_name1].append(res1)
                            graphs_no_match[uid][func_name1 + '_new'].append(res2)
                            graphs_no_match[uid]['total_similiarity1'].append(sim_matrixOLD_noNN[index1][index2])
                            graphs_no_match[uid]['total_similiarity2'].append(sim_matrixOLD_NN[index1][index2])
                            graphs_no_match[uid]['total_similiarity3'].append(sim_matrixNEW_noNN[index1][index2])

                            correlations[func_name1].append([res1, res2])
                            covariances[func_name1].append([res1, res2])
                            disc = 1 if abs(res1 - res2) > 0.25 else 0
                            discrepancies[func_name1].append(disc)

                            if func_name1 == 'compare_computed_styles' and abs(res1 - res2) > 0.2:  # and res1 != 0.5000139814:
                                ld1 = elem_descriptions_by_id[id1]
                                ld2 = elem_descriptions_by_id[id2]
                                # if res1 == 0.5000139814 or res1 == 1:
                                #     continue
                                #import pdb; pdb.set_trace()

        clusters_by_id = {}
        for cluster in di['cluster_ids']:
            for id in cluster:
                clusters_by_id[id] = cluster

        correlationsCC1, correlationsCC2 = [], []
        discrepanciesCC1, discrepanciesCC2 = [], []

        for ld1 in di['results_new']['elem_descriptions']:
            for ld2 in di['results_new']['elem_descriptions']:
                if ld1['node_id'] == ld2['node_id']:
                    continue
                id1, id2 = ld1['node_id'], ld2['node_id']
                index1 = ids.index(id1)
                index2 = ids.index(id2)
                res1 = di['results_old']['matrix_results']['compare_computed_styles']['%s__%s' % (id1, id2)]
                res2 = di['results_new']['matrix_results']['compare_computed_styles']['%s__%s' % (id1, id2)]
                nn_sim = sim_matrixOLD_noNN[index1][index2]

                if id1 in clusters_by_id and id2 in clusters_by_id:
                    if id1 in clusters_by_id[id2] or id2 in clusters_by_id[id1]:
                        nn_sim *= 0.85
                    else:
                        nn_sim *= 1.08

                correlationsCC1.append(
                    (res1, nn_sim)
                )
                correlationsCC2.append(
                    (res2, nn_sim)
                )
                discrepanciesCC1.append(abs(nn_sim-res1))
                discrepanciesCC2.append(abs(nn_sim-res2))

        vals1, vals2 = [tup[0] for tup in correlationsCC1], [tup[1] for tup in correlationsCC1]
        correlationsCC1 = np.corrcoef(vals1, vals2)[0][1]
        vals1, vals2 = [tup[0] for tup in correlationsCC2], [tup[1] for tup in correlationsCC2]
        correlationsCC2 = np.corrcoef(vals1, vals2)[0][1]
        discrepanciesCC1 = np.mean(discrepanciesCC1)
        discrepanciesCC2 = np.mean(discrepanciesCC2)

        import pdb; pdb.set_trace()

        for func_name, results in correlations.items():
            vals1, vals2 = [tup[0] for tup in results], [tup[1] for tup in results]
            correlations[func_name] = np.corrcoef(vals1, vals2)[0][1]
        for func_name, results in covariances.items():
            vals1, vals2 = [tup[0] for tup in results], [tup[1] for tup in results]
            covariances[func_name] = np.mean(np.cov(vals1, vals2))
        for func_name, results in discrepancies.items():
            score = 1 - (sum(results) / len(results))
            discrepancies[func_name] = score

        print('WARNING: temp exit()')
        exit()

        print()

        figure_dir = '/home/ross/code/events_project/webextractor/webextractor/clustering/ground_truth/data/cluster_data/' + uid + '_match_plots' + '/'
        if not os.path.exists(figure_dir):
            os.makedirs(figure_dir)

        for func_name, results in graphs_match[uid].items():
            fp = figure_dir + func_name + '.png'
            create_historgram(results, fp)

        figure_dir = '/home/ross/code/events_project/webextractor/webextractor/clustering/ground_truth/data/cluster_data/' + uid + '_mismatch_plots' + '/'
        if not os.path.exists(figure_dir):
            os.makedirs(figure_dir)

        for func_name, results in graphs_no_match[uid].items():
            fp = figure_dir + func_name + '.png'
            create_historgram(results, fp)

        # todo: measure correlations between old and new functions

        import pdb; pdb.set_trace()
        print()


'''
issues:
---------


image links wrong sizes rect:
https://www.gasworks.org.uk/events/
https://neweconomy.net/events 
https://www.csis.org/events-upcoming?title=
https://www.ucl.ac.uk/laws/

https://www.chathamhouse.org/events/all  - screenshot not working
https://nowtoronto.com/search/event/all/#page=1 - image rects misaligned


get_parent_paths_multiple() fails:
https://waronwant.org/news-and-events
https://www.advayainitiative.com/upcoming-events/
https://www.cps.org.uk/events/
'https://www.republicofwork.com/upcoming/?view=calendar&month=October-2018',
'https://www.city.ac.uk/events/2018/september',
'https://shecancode.io/attend-events/',
    'https://rusi.org/events',
'https://sparc.london/events/',
    
TypeError: cannot serialize '_io.TextIOWrapper' object
'https://piie.com/events', 

errors with old implementation, try with new:
'http://www.blogto.com/events/',
'https://www.rgs.org/events/',
'https://knpr.org/events',
'https://www.gsb.stanford.edu/events',
    'https://www.kent.ac.uk/calendar/?view_by=week&date=20180128&category=&tag=',
    'https://www.kingsplace.co.uk/whats-on/page/4/',
    'http://www.panafricanthought.com/events/',
    
    'http://www.lse.ac.uk/european-institute/events',
    
    
"$ is not a function" error
'https://dublin.sciencegallery.com/events',
'https://www.alternatives.org.uk/events',
'''

GT_URLS = [

    # skipped (not good training examples)
    'http://www.lighthouse.org.uk/programme/#filter=.events',
    'https://openeurope.org.uk/action/events/',
    'https://www.bvca.co.uk/Calendar',
    'http://hackoustic.org/events/',
    # finished
    'https://www.ucl.ac.uk/events/', 'https://soas.ac.uk/about/events', 'https://civichall.org/event-calendar/',
    'https://www.weforum.org/events', 'https://citizenlab.ca/category/lab-news/events/',
    'https://www.gasworks.org.uk/events/', 'https://www.centreforlondon.org/events/upcoming-events/',
    'https://kingschurchlondon.org/calendar/', 'https://about.gitlab.com/events/',
    'https://kingschurchlondon.org/events/', 'https://www.stanford.edu/events/',
    'https://ccrma.stanford.edu/workshops', 'https://www.gamesindustry.biz/network/events',
    'https://dublin.sciencegallery.com/events', 'https://www.alternatives.org.uk/events',
    'http://www.lsbu.ac.uk/whats-on', 'https://tokenmarket.net/ico-calendar',
    'http://kingscross.impacthub.net/events/',
    'https://neweconomy.net/events', 'https://www.artsadmin.co.uk/events',
    'https://www.csis.org/events-upcoming?title=',
    'http://live.worldbank.org/event-finder',
    'https://www.harvard.edu/events',
    'https://theodi.org/events',
    'http://elitebusinessmagazine.co.uk/events',
    'https://www.englandathletics.org/england-athletics-events',
    'https://www.joyent.com/events',
    'http://www.iamhiphopmagazine.com/events/', 'https://womensagenda.com.au/events',
    'http://www.bristol.ac.uk/arts/events/',
    'http://www.lse.ac.uk/Events/Search-Events',
    'https://giantswarm.io/events/',
    'http://team.localist.com', 'http://www.slow-journalism.com/filter/events-and-classes',
    'http://www.bbk.ac.uk/events/?tagfilter=&currentCategoryType=&browseby=4',
    'http://www.presbyterianireland.org/Events.aspx', 'https://www.powertochange.org.uk/events/', 'https://www.authentic-eros.com/de/kalender',
    'http://www.ox.ac.uk/events-list', 'https://www.startupbootcamp.org/events/',
    'https://www.belfercenter.org/events/', 'http://www.spacestudios.org.uk/technology-cats/courses-wo/',
    'https://www.somersethouse.org.uk/whats-on?title=&field_theme_tid%5B0%5D=37',
    'https://swisschurchlondon.org.uk/events/', 'https://dublin2019.com/category/events/',
    'http://www.tripspace.co.uk/programme/current/',
    'https://www.ucl.ac.uk/laws/', 'https://uk.funzing.com/lectures?from_date=07/09/2018&address=London,%20UK&city=London',
    'https://digiday.com/events/', 'http://www.bbk.ac.uk/bisr/bigs/2017-18-events', 'https://www.nationalpoetrylibrary.org.uk/events-exhibitions',
    'https://www.richmix.org.uk/events/type/music',
    'https://www.theparisreview.org/events', 'http://www.academyofideas.org.uk/events',
    'https://www.visitdublin.com/whats-on', 'http://www.bookbrunch.co.uk/page/events/?ds=Events',
    'https://www.plutobooks.com/events/', 'https://www.uvm.edu/~uvmpr/?Page=EMS&SM=eventssub.html',
    'https://www.tuc.org.uk/events', 'https://www.transform-network.net/calendar/',
    'https://www.re-work.co/events/',
    'https://www.jrf.org.uk/our-work/events',
    'http://blackhistorystudies.com/events/',
    'https://www.epi.org/events/',
    'https://alumni-gsb.stanford.edu/get/page/events',
    'https://www.sas.ac.uk/events?institute_id=347',
    'https://amadeus.com/en/events.upcoming',
    'https://www.cptheatre.co.uk/whats-on/upcoming-shows/',
    'https://www.chch.ox.ac.uk/events',
    'https://www.iod.com/events-community/regions/london/events',
    'https://www.coworkinglondon.com/tech-events/',
    'http://insight.jbs.cam.ac.uk/events/',
    'https://www.pcgamesinsider.biz/events/',
    'https://soas.ac.uk/about/events',
    # skipped
    'http://heyevent.com/london',

]

if __name__ == '__main__':

    for url in GT_URLS:
        create_ground_truth(url)

    #get_training_urls()

    #create_historgram(None)

    #create_ground_truth(url)
    #generate_sim_measurement_report()

    exit()