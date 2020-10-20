from collections import defaultdict
import datetime
import json
from os import environ
import pika
import redis
import uuid

from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing import Pool as ProcessPool

from util_core.api.redis_api import redis__wait_for_key, SimMatrixRedisClient
from util_core.api.s3_api import get_s3_client
from util_core.api.task_tracker_api import (
    TT__create_model
)
from util_core.util.vuejs import create_vue_elem_dict
from webextractor.clustering.comparisons.area_similarity import areas_similar
from webextractor.clustering.comparisons.computed_styles import compare_computed_styles
from webextractor.clustering.comparisons.content import compare_content
from webextractor.clustering.comparisons.euclidean_distance import adjusted_euclidean_distance
from webextractor.clustering.comparisons.featureset_overlap import featureset_overlap
from webextractor.clustering.comparisons.is_visible import compare_visibility
from webextractor.clustering.comparisons.navigation_status import compare_navigation_status
from webextractor.clustering.comparisons.spatial_alignment import spatially_aligned
from webextractor.clustering.comparisons.url_similarity import url_similarity
from webextractor.clustering.comparisons.visual_similarity import visually_similar
from webextractor.clustering.util import get_clusters_dbscan
from webextractor.selenium_wrapper.main import FirefoxDriverWrapper
from webextractor.selenium_wrapper.preloading import preload_element_data
from webextractor.element_descriptions.descriptions import ElemDescription
from webextractor.process_controller_util.util import create_context
from webextractor.visual.util import ImageRect

COMPARISON_FUNCTIONS = [
    areas_similar,
    compare_computed_styles,
    compare_content,
    adjusted_euclidean_distance,
    featureset_overlap,
    compare_visibility,
    compare_navigation_status,
    spatially_aligned,
    url_similarity,
    visually_similar
]

AMQP_URL = environ['CELERY_BROKER_URL']
PIKA_PARAMS = pika.connection.URLParameters(AMQP_URL)


def get_computed_style_weights(elem_descriptions):

    counts = defaultdict(int)
    for ed in elem_descriptions:
        for key, val in ed['all_computed_styles'].items():
            counts[(key, val)] += 1
    coefficients = {}
    for key_val, count in counts.items():
        coefficients[key_val] = count / len(elem_descriptions)
    return coefficients


def get_distances(elem_descriptions, func, context, relevant_comparisons=None):
    bf = datetime.datetime.now()
    results = []
    for i, ld1 in enumerate(elem_descriptions):
        id1 = ld1['node_id']
        for j, ld2 in enumerate(elem_descriptions):
            if i >= j:
                continue
            id2 = ld2['node_id']
            if relevant_comparisons:
                if (id1, id2) not in relevant_comparisons and (id2, id1) not in relevant_comparisons:
                    results.append(-1)
                    continue
            dist = func(ld1, ld2, context)
            results.append(dist)
    af = datetime.datetime.now()
    print('get_distances() %s time: %s' % (func.__name__, (af - bf).seconds))
    return results


'''
def compress_matrix_results(matrix_results):

    combo_keys = [k for k in matrix_results['areas_similar'].keys()]
    compressed_keys, compressed_keys_REV = {}, {}
    for i, key in enumerate(combo_keys):
        c_key = num_encode(i)
        compressed_keys[c_key] = key
        compressed_keys_REV[key] = c_key
    for func_name, matrix in matrix_results.items():
        for key in combo_keys:
            c_key = compressed_keys_REV[key]
            matrix[c_key] = matrix[key]
            del matrix[key]

    return matrix_results, compressed_keys_REV
'''


def get_matrix_results(driver, elem_descriptions, screenshot_task, context, relevant_comparisons=None):
    bf = datetime.datetime.now()
    MULTI = False

    matrix_results = {}
    if MULTI:
        pool = ProcessPool(processes=7)
        for func in COMPARISON_FUNCTIONS:
            if func.__name__ in ('visually_similar', 'compare_navigation_status'):
                continue
            matrix_results[func.__name__] = pool.apply_async(
                get_distances, (elem_descriptions, func, context, relevant_comparisons)
            )
    else:
        for func in COMPARISON_FUNCTIONS:
            if func.__name__ in ('visually_similar', 'compare_navigation_status'):
                continue
            matrix_results[func.__name__] = get_distances(
                elem_descriptions, func, context, relevant_comparisons
            )

    if screenshot_task:
        screenshot_task.wait()
    context.update(driver.screenshot_data)

    img_rect_eds = []
    for ed in elem_descriptions:
        img_rect_eds.append({
            'node_id': ed['node_id'], 'driver__is_displayed': ed['driver__is_displayed'],
            'img_rect': ImageRect(ed['rect'], context)
        })
    matrix_results['visually_similar'] = get_distances(
        img_rect_eds, visually_similar, context, relevant_comparisons
    )
    if MULTI:
        for func in COMPARISON_FUNCTIONS:
            if func.__name__ in ('visually_similar', 'compare_navigation_status'):
                continue
            matrix_results[func.__name__] = matrix_results[func.__name__].get()

    af = datetime.datetime.now()
    print('get_matrix_results() total time: %s' % (af-bf).seconds)

    return matrix_results


import inspect


class KeyTracker(dict):

    def __init__(self, *args, **kwargs):
        self.log = defaultdict(set)
        super(KeyTracker, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        func_name = inspect.stack()[1].function
        self.log[func_name].add(key)
        return super(KeyTracker, self).__getitem__(key)


def do_stuff(url, driver=None):
    from util_core.util.draw import draw_clusters_on_driver

    driver = driver or FirefoxDriverWrapper()
    driver.initialise_for_clustering(url)
    elems = driver.get_link_elements()  # driver.find_elements_by_xpath('//a')

    # nav_task = NavTask(
    #     links, url, driver.page_source
    # )
    bf = datetime.datetime.now()
    context = create_context(driver, url, get_screenshot=False)

    elem_descriptions = [
        ElemDescription.create(e, i, context).to_dict()
        for (i, e) in enumerate(elems)
    ]
    # elem_descriptions_by_id = {ed['node_id']: ed for ed in elem_descriptions}
    af = datetime.datetime.now()
    print('time to get context and elem_descriptions: %s' % (af-bf).seconds)

    context['computed_style_weights'] = get_computed_style_weights(elem_descriptions)

    thread_pool = ThreadPool(2)
    screenshot_task = thread_pool.apply_async(driver.get_screenshot_data)

    #elem_descriptions[0]['log'] = defaultdict(set)
    elem_descriptions[0] = KeyTracker(elem_descriptions[0])

    matrix_results = get_matrix_results(  # also gets screenshot
        driver, elem_descriptions, screenshot_task, context
    )
    thread_pool.close()

    elem_ids, sim_matrix = request_sim_matrix(
        elem_descriptions, matrix_results, context
    )

    cluster_objects, _, leftover_ids = get_clusters_dbscan(
        sim_matrix, elem_descriptions, eps=0.407
    )

    rabbitmq_reply_queue = 'webextractor_reply_' + uuid.uuid4().hex

    print('warning: screenshot s3 upload disabled')
    screenshot_s3_url = None
    # _, screenshot_s3_url = get_s3_client().upload_screenshot(
    #     context['screenshot_fp']
    # )
    cluster_ids = [c.node_ids for c in cluster_objects]
    elements_by_id = {
        ed['node_id']: create_vue_elem_dict(ed) for ed in elem_descriptions
    }

    create_model_di = {
        'cluster_ids': cluster_ids,
        'leftover_ids': leftover_ids,
        'elements_by_id': elements_by_id,
        'rabbitmq_queue': rabbitmq_reply_queue,
        'screenshot_s3_url': screenshot_s3_url,
        'screenshot_height': context['screenshot_obj'].height,
        'status': 'pending_cluster_selection',
    }
    succ, cluster_results_pk = TT__create_model(
        'workflow.ClusterResults', create_model_di
    )
    draw_clusters_on_driver(driver, cluster_objects)

    return driver, cluster_objects, context

    chosen = int(input('choose a cluster').strip())
    from webextractor.column_finder_list.main import ListPageColumnFinder
    data = ListPageColumnFinder(driver, cluster_objects[chosen]).extract_table()
    # from column_finder_list.main import TemplateFinderNew2
    # data = TemplateFinderNew2(driver, cluster_objects[chosen]).extract_table()

    '''
    listpage columns: 
    
    from sibling_processor.main.column_finder_new3 import ColumnFinder
    cluster_urls = [ld['url'] for ld in link_clusters[num] if ld['url']][:16] # todo: temporarily capping it to 7 urls
    ColumnFinder().get_columns(cluster_urls, single_threaded=True)    
    '''

    '''
    rabbitmq_channel = pika.BlockingConnection(PIKA_PARAMS).channel()
    rabbitmq_channel.queue_declare(rabbitmq_reply_queue)

    print('waiting for messages...')  # (cluster_results_pk, rabbitmq_reply_queue))
    rabbitmq_channel.basic_consume(
        rabbitmq_reply_queue, _vue_response_received,
        # auto_ack=True is the fire and forget mode
        auto_ack=True
    )
    try:
        rabbitmq_channel.start_consuming()
    except KeyboardInterrupt:
        rabbitmq_channel.stop_consuming()
    rabbitmq_channel.close()'''

    '''
    draw_clusters_on_driver(driver, cluster_objects)
    import pdb; pdb.set_trace()
    driver.quit()'''


def _vue_response_received(ch, method, properties, body):
    msg = json.loads(body.decode())
    print('msg received:  ' + str(msg))


def request_sim_matrix(elem_descriptions, matrix_results, context, relevant_comparisons=None):
    uid = uuid.uuid4().hex
    redis_resultkey = 'SimMatrix__' + uid
    redis_waitkey = 'WaitKey__' + uid

    context = context.copy()
    if 'screenshot_obj' in context:
        del context['screenshot_obj']
    if 'screenshotQ_obj' in context:
        del context['screenshotQ_obj']
    if 'computed_style_weights' in context:
        del context['computed_style_weights']

    elem_descriptions = elem_descriptions.copy()
    for i, ed in enumerate(elem_descriptions):
        ed['all_computed_styles__array'] = list(ed['all_computed_styles__array'])
        if 'ancestor_path' in ed:
            del ed['ancestor_path']

    msg = {
        'task_type': 'sim_matrix_task',
        'context': context,
        'element_descriptions': elem_descriptions,  # do we even need this?
        'matrix_results': matrix_results,
        'redis_wait_key': redis_waitkey,
        'expected_result_key': redis_resultkey,
        'relevant_comparisons': relevant_comparisons
    }

    rabbitmq_connection = pika.BlockingConnection(PIKA_PARAMS)
    rabbitmq_connection.channel().basic_publish(
        exchange='', body=json.dumps(msg).encode(),
        routing_key='webextractor_ft__sim_matrix_tasks',
    )

    print('waiting for SimMatrixResult (key: %s)' % redis_waitkey)
    redis_client = SimMatrixRedisClient()
    redis__wait_for_key(redis_waitkey, client=redis_client)
    elem_ids, sim_matrix = redis_client.get_sim_matrix(redis_resultkey)
    redis_client.delete_sim_matrix(redis_resultkey)
    return elem_ids, sim_matrix


if __name__ == '__main__':

    urls = [
        'https://www.stanford.edu/events/',
        'https://ccrma.stanford.edu/workshops', 'https://www.gamesindustry.biz/network/events',
        'http://www.lsbu.ac.uk/whats-on', 'https://tokenmarket.net/ico-calendar',
        'http://kingscross.impacthub.net/events/',
        'https://neweconomy.net/events', 'https://www.artsadmin.co.uk/events',
    ]
    for u in urls:
        do_stuff(u)
    #do_stuff('https://soas.ac.uk/about/events')
    #do_stuff('https://www.ucl.ac.uk/events/')
    #do_stuff('https://www.royalalberthall.com/tickets')
