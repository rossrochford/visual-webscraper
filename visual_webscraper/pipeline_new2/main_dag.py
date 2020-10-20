from collections import defaultdict
import json
import os
import uuid

import trio

from ws_model.models import WsRedisModel
from ws_model.main_daemon import start_ws_model_server

from trio_graph_scheduler.execution import execute_graph
from trio_graph_scheduler.graph import TaskGraph

from webextractor.clustering.util import get_clusters_dbscan
from webextractor.clustering_rust.rust_descs import (
    get_sims__url, get_sims__css, get_sims__feature_set, get_sims__rect,
    get_sims__visibility, get_sims__content_concurrent, get_sims__content
)
from webextractor.column_finder_detail2.main import find_detailpage_columns
from webextractor.element_descriptions.feature_set import create_feature_set2
from webextractor.util_new.trio_util import TrioRedisClient
from selenium_trio.remote_webdriver import TrioAsyncDriver
# from webextractor.selenium_wrapper.elements import WebElementWrapper, LinkWebElementWrapper
# from webextractor.selenium_wrapper.preloading import get_parent_paths_multiple as _get_parent_paths_multiple
# from webextractor.pipeline_new.util import resize_driver, get_screenshot_data
# from webextractor.pipeline_new2.clustering import get_matrix_results__python
from webextractor.pipeline_new2.util import resize_driver, get_page_height, create_pickleable_attrdict
from webextractor.pipeline_new2.util import get_screenshot_data as _get_screenshot_data
from webextractor.pipeline_new2.elem_processing import (
    process_outer_html__url, process_ancestor_paths, process_xpaths,
    process_rects, process_computed_styles
)
from selenium_trio.extras.preloading import get_parent_paths_multiple as _get_parent_paths_multiple
from selenium_trio.extras.preloading import get_rect_multiple as _get_rect_multiple
from selenium_trio.extras.preloading import get_computed_css_multiple as _get_computed_css_multiple
from selenium_trio.extras.preloading import (
    get_multiple_outer__chunk, get_xpaths_multiple
)
from util_core.util.serialisation import pickle_dumps_str
from util_core.util.urls_util import url_host, url_base
from webextractor.util_new.s3_util import s3_file_upload, s3_json_upload
from webextractor.visual.main import get_visual_similarities
from ws_model.ws_client import TrioWebSocketClient


VISIBILITY_KEYS = [
    'visibility__ALL_VISIBLE',
    'cssComputed__visibility',
    'jquery__is_hidden',
    'cssComputed__display',
    'spatial_visibility',
    'driver__is_displayed'
]

ALL_VISIBLE = {
    'cssComputed__visibility': 'visible',
    'jquery__is_hidden': False,
    'driver__is_displayed': True,
    'spatial_visibility': 'IN_PAGE'
}  # 'cssComputed__display': 'block'}

VUEJS_DESC_FIELDS = [
    'text',
    'node_id',
    'rect',
    'tag_name'
]

REDIS_HOSTNAME = os.environ.get('REDIS_HOSTNAME', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

SELENIUM_DRIVER_TYPE = os.environ.get('SELENIUM_DRIVER_TYPE', 'local')
assert SELENIUM_DRIVER_TYPE in ('selenoid', 'local')

WEBSOCKET_PORT = 8086


async def get_parent_paths_multiple(driver, driver_elems):
    '''
    for path in ancestor_paths:
        for elem_dict in path:
            elem = elem_dict['elem']
            # todo: do we need this?
            #elem_dict['elem'] = create_pickleable_attrdict(
            #    elem, ['id', 'tag_class_str', 'attrs']
            #)
    '''
    return await _get_parent_paths_multiple(driver, driver_elems, wrap=True)


async def launch_driver(cluster_task_model_uid, page_url, **kwargs):

    if SELENIUM_DRIVER_TYPE == 'local':
        driver = await TrioAsyncDriver.create_local_driver()
    elif SELENIUM_DRIVER_TYPE == 'selenoid':
        driver = await TrioAsyncDriver.create_selenoid_driver()
    else:
        raise Exception('invalid value of SELENIUM_DRIVER_TYPE: %s' % SELENIUM_DRIVER_TYPE)

    kwargs['graph'].driver = driver

    await driver.get2(page_url)
    link_elems = await driver.find_elements_by_xpath2('//a')

    driver.page_sourceL = (await driver.page_source2).lower()

    context = {
        'pipeline_session_uid': cluster_task_model_uid,
        'page_url': page_url,
        'page_url_host': url_host(page_url),
        'page_host_base': url_base(page_url),
        'quick': True,
        'link_elems': link_elems,
        'feature_string_to_num': {},
        'computed_style_string_to_num': {},
        'partial_descs': [],
        'elem_descs_consolidated': {},  # descs by id
        'consolidation_lock': trio.Lock(),  # lock for when doing consolidation
    }

    kwargs['graph'].context = context

    return driver, link_elems, context


async def get_outer_html_and_ancestors(**kwargs):
    graph = kwargs['graph']
    _, predecessors = kwargs['task_node'].get_predecessor_task_nodes()

    if 'launch_driver' in predecessors:
        elems = predecessors['launch_driver'][0].task_result[1]
    elif 'resize_browser' in predecessors:
        elems = predecessors['resize_browser'][0].task_result
    else:
        print('warning: get_outer_html_and_ancestors() has no valid predecessors')
        return

    elem_ids = [e.id for e in elems]

    outer_htmls = await get_multiple_outer__chunk(graph.driver, elems)

    ancestor_paths = await get_parent_paths_multiple(graph.driver, elems)

    partial_descs = process_outer_html__url(elem_ids, outer_htmls, graph.context)
    partial_descs2 = process_ancestor_paths(elem_ids, ancestor_paths)

    return partial_descs + partial_descs2


async def resize_browser(**kwargs):
    graph, task_node = kwargs['graph'], kwargs['task_node']
    driver, context = graph.driver, graph.context

    #existing_link_elems = context['link_elems']  # predecessors['launch_driver'][0].task_result[1]
    #existing_link_elem_ids = [e.id for e in existing_link_elems]

    await resize_driver(driver, 0.6)

    context['page_height'] = await get_page_height(driver)

    return None


async def check_for_new_elems_after_resize(**kwargs):

    graph, task_node = kwargs['graph'], kwargs['task_node']
    driver, context = graph.driver, graph.context

    existing_link_elems = context['link_elems']  # predecessors['launch_driver'][0].task_result[1]
    existing_link_elem_ids = [e.id for e in existing_link_elems]
    link_elems = await driver.find_elements_by_xpath2('//a')
    new_link_elems = [e for e in link_elems if e.id not in existing_link_elem_ids]

    if new_link_elems:
        context['link_elems'].extend(new_link_elems)
        elem_ids = [e.id for e in new_link_elems]

        outer_htmls = await get_multiple_outer__chunk(graph.driver, new_link_elems)
        ancestor_paths = await get_parent_paths_multiple(graph.driver, new_link_elems)

        partial_descs = process_outer_html__url(elem_ids, outer_htmls, graph.context)
        partial_descs2 = process_ancestor_paths(elem_ids, ancestor_paths)

        return partial_descs + partial_descs2

    return None


async def get_xpaths(**kwargs):

    graph, task_node = kwargs['graph'], kwargs['task_node']
    _, predecessors = task_node.get_predecessor_task_nodes()
    driver, context = graph.driver, graph.context

    # partial_descs = predecessors['get_outer_html_and_ancestors'][0].task_result
    # todo: check for second predecessor

    xpaths = await get_xpaths_multiple(driver, context['link_elems'])

    elem_ids = [e.id for e in context['link_elems']]
    partial_descs = process_xpaths(elem_ids, xpaths)
    return partial_descs


async def get_screenshot_data(**kwargs):

    graph, driver = kwargs['graph'], kwargs['graph'].driver

    ss_data = await _get_screenshot_data(driver)

    s3_key, screenshot_url = await trio.to_thread.run_sync(
        s3_file_upload, 'webpage-screenshots',
        ss_data['screenshot_fp'], 'image/png', 'png'
    )

    # hack, front-end accesses the image via the host machine, amending url here
    s3_host = os.environ.get('S3_HOST', '127.0.0.1')
    screenshot_url = screenshot_url.replace(s3_host, '127.0.0.1')

    await graph.ws_cli.send({
        'view': 'update_object',
        'model': 'ClusterTask', 'uid': graph.cluster_task_model_uid,
        'fields': {
            'screenshotUrl': screenshot_url,
            'screenshotHeight': ss_data['screenshot_height']
        }
    })

    return ss_data


async def get_rect_multiple(**kwargs):

    graph = kwargs['graph']
    driver, context = graph.driver, graph.context

    elem_ids = [e.id for e in context['link_elems']]
    rects = await _get_rect_multiple(driver, context['link_elems'])

    partial_descs = process_rects(elem_ids, rects)
    return partial_descs


async def get_computed_css_multiple(**kwargs):
    graph = kwargs['graph']
    driver, context = graph.driver, graph.context

    elem_ids = [e.id for e in context['link_elems']]
    rects = await _get_computed_css_multiple(driver, context['link_elems'])

    partial_descs = process_computed_styles(elem_ids, rects, context)
    return partial_descs


async def get_display_multiple(**kwargs):
    graph, task_node = kwargs['graph'], kwargs['task_node']
    driver, context = graph.driver, graph.context

    quick_mode = False

    _, predecessors = task_node.get_predecessor_task_nodes()

    partial_descs__css = predecessors['get_computed_css_multiple'][0].task_result
    partial_descs__css = {ed['node_id']: ed for ed in partial_descs__css}

    partial_descs = []
    for elem in context['link_elems']:
        ed = partial_descs__css[elem.id]

        if 'jquery__is_hidden' in ed and ed['jquery__is_hidden']:
            is_displayed = False if quick_mode else (await elem.is_displayed2())
        else:
            is_displayed = True
        partial_descs.append({
            'node_id': elem.id, 'driver__is_displayed': is_displayed
        })

    return partial_descs


'''
def get_featureset_multiple(elem_ids, descs_by_id):
    return [
        create_feature_set2(descs_by_id[id]) for id in elem_ids
    ]

def _add_featureset_integers(collection, partial_descs_by_id):
    for id, ed in partial_descs_by_id.items():
        ed['feature_set_int'] = [None for _ in ed['feature_set']]
        for i, ft in enumerate(ed['feature_set']):
            key = ft
            if key not in collection.feature_string_to_num:
                collection.feature_string_to_num[key] = len(collection.feature_string_to_num)
            ed['feature_set_int'][i] = collection.feature_string_to_num[key]

def process_feature_sets(collection, elem_ids, data_items):

    partial_descs_by_id = {}
    for i, id in enumerate(elem_ids):
        partial_descs_by_id[id] = {
            'feature_set': data_items[i], 'node_id': id
        }

    if CONVERT_TO_NUMS:
        with collection.lock:
            _add_featureset_integers(collection, partial_descs_by_id)

    return partial_descs_by_id
'''


async def get_featureset_multiple(**kwargs):

    context = kwargs['graph'].context
    feature_string_to_num = context['feature_string_to_num']
    existing_descs = context['elem_descs_consolidated']

    partial_descs = []
    for node_id, ed in existing_descs.items():

        # todo: tidy this up into one function

        feature_set = create_feature_set2(ed)
        feature_set_int = [None for _ in feature_set]
        for i, ft in enumerate(feature_set):
            key = ft
            if key not in feature_string_to_num:
                feature_string_to_num[key] = len(feature_string_to_num)
            feature_set_int[i] = feature_string_to_num[key]

        partial_desc = {
            'node_id': node_id,
            'feature_set':  feature_set,
            'feature_set_int': set(feature_set_int)
        }

        partial_descs.append(partial_desc)
    return partial_descs


async def get_visual_sims(**kwargs):

    task_node, context = kwargs['task_node'], kwargs['graph'].context
    existing_descs = context['elem_descs_consolidated']

    _, predecessors = task_node.get_predecessor_task_nodes()
    screenshot_data = predecessors['get_screenshot_data'][0].task_result

    existing_descs = [ed for (id, ed) in existing_descs.items()]
    #elem_ids = [ed['node_id'] for ed in existing_descs]

    # should really be done in a separate process rather than a thread
    _, visual_sims = await trio.to_thread.run_sync(
        get_visual_similarities, existing_descs, screenshot_data
    )

    return visual_sims


async def consolidate_descs(**kwargs):

    task_node = kwargs['task_node']
    context = kwargs['graph'].context

    _, predecessors = task_node.get_predecessor_task_nodes()

    partial_descs1 = predecessors['get_outer_html_and_ancestors'][0].task_result
    partial_descs2 = predecessors['get_xpaths'][0].task_result
    partial_descs3 = predecessors['get_rect_multiple'][0].task_result
    partial_descs4 = predecessors['get_computed_css_multiple'][0].task_result
    partial_descs5 = predecessors['check_for_new_elems_after_resize'][0].task_result or []
    partial_descs6 = predecessors['get_display_multiple'][0].task_result

    partial_descs = (
        partial_descs1 + partial_descs2 + partial_descs3 +
        partial_descs4 + partial_descs5 + partial_descs6
    )
    existing_descs = context['elem_descs_consolidated']

    async with context['consolidation_lock']:
        _consolidate_descs(existing_descs, partial_descs)


async def consolidate_descs2(**kwargs):

    task_node = kwargs['task_node']
    context = kwargs['graph'].context

    _, predecessors = task_node.get_predecessor_task_nodes()

    partial_descs = predecessors['get_featureset_multiple'][0].task_result
    existing_descs = context['elem_descs_consolidated']

    async with context['consolidation_lock']:
        _consolidate_descs(existing_descs, partial_descs)

    # add visibility__ALL_VISIBLE
    for id, desc in existing_descs.items():
        desc['visibility__ALL_VISIBLE'] = True
        if desc['cssComputed__display'] == 'none':
            desc['visibility__ALL_VISIBLE'] = False
            continue
        for key, visible_val in ALL_VISIBLE.items():
            if desc[key] != visible_val:
                desc['visibility__ALL_VISIBLE'] = False
                break

    return None


def _consolidate_descs(existing_descs, partial_descs):

    partial_descs_by_id = defaultdict(list)
    for ed in partial_descs:
        partial_descs_by_id[ed['node_id']].append(ed)

    for id, descs in partial_descs_by_id.items():
        values_by_key = defaultdict(list)
        for ed in descs:
            for key, val in ed.items():
                if val not in values_by_key[key]:
                    values_by_key[key].append(val)
        new_desc = {}
        for key, vals in values_by_key.items():
            if id in existing_descs and key in existing_descs[id]:
                if existing_descs[id][key] not in vals:  # probably will never true
                    vals.append(existing_descs[id][key])
            vals.sort(reverse=True)  # sort so any blank/none values are last
            new_desc[key] = vals[0]

        if id in existing_descs:
            existing_descs[id].update(new_desc)
        else:
            existing_descs[id] = new_desc


async def _get_sims(existing_descs_li, context):
    context_for_rust = {
        'page_url': context['page_url'],
        'page_url_host': context['page_url_host'],
        'page_height': context['page_height'],
        'quick': context['quick']
    }
    existing_desc_rects = [ed['rect'] for ed in existing_descs_li]

    # cpu intensive, doing this in a thread so it doesn't hold up the event-loop
    content_sims = await trio.to_thread.run_sync(
        get_sims__content_concurrent, existing_descs_li, context_for_rust
    )

    area_sims, euclidean_sims, spatially_aligned_sims, area_alignment_sims = get_sims__rect(
        existing_desc_rects, context_for_rust
    )
    matrix_results = {
        'adjusted_euclidean_distance': euclidean_sims,
        'areas_similar': area_sims,
        'area_alignment_simple': area_alignment_sims,
        'compare_content': content_sims,
        'spatially_aligned': spatially_aligned_sims,

        'featureset_overlap': get_sims__feature_set(existing_descs_li, context_for_rust),
        'url_similarity': get_sims__url(existing_descs_li, context_for_rust),
        'compare_computed_styles': get_sims__css(existing_descs_li, context_for_rust),

        'compare_visibility': get_sims__visibility(existing_descs_li, context_for_rust)
    }
    return matrix_results


def _push_amqp_msg(queue_name, msg_str):
    import pika
    AMQP_URL = os.environ['CELERY_BROKER_URL']
    PIKA_PARAMS = pika.connection.URLParameters(AMQP_URL)
    rabbitmq_connection = pika.BlockingConnection(PIKA_PARAMS)
    rabbitmq_connection.channel().basic_publish(
        exchange='', body=msg_str.encode(),
        routing_key=queue_name,
    )


def _push_redis_msg(queue_name, msg_str):
    import redis
    cli = redis.StrictRedis(host=REDIS_HOSTNAME, port=REDIS_PORT)
    cli.lpush(queue_name, msg_str)


def request_sim_matrix(elem_descriptions, matrix_results, context, relevant_comparisons=None):

    from util_core.api.redis_api import redis__wait_for_key, SimMatrixRedisClient

    uid = uuid.uuid4().hex
    queue_name = 'webextractor_ft__sim_matrix_tasks'
    redis_resultkey = 'SimMatrix__' + uid
    redis_waitkey = 'WaitKey__' + uid

    context2 = {
        'pipeline_session_uid': context['pipeline_session_uid'],
        'page_url': context['page_url'],
        'page_url_host': context['page_url_host'],
        'page_host_base': context['page_host_base'],
        'page_height': context['page_height'],
        'quick': context['quick']
    }
    '''
    context = context.copy()
    if 'screenshot_obj' in context:
        del context['screenshot_obj']
    if 'screenshotQ_obj' in context:
        del context['screenshotQ_obj']
    if 'computed_style_weights' in context:
        del context['computed_style_weights']
    '''

    elem_descriptions = elem_descriptions.copy()
    for i, ed in enumerate(elem_descriptions):
        ed['all_computed_styles__array'] = list(ed['all_computed_styles__array'])
        if 'ancestor_path' in ed:
            del ed['ancestor_path']
        ed['feature_set_int'] = [n for n in ed['feature_set_int']]

    msg = {
        'task_type': 'sim_matrix_task',
        'context': context2,
        'element_descriptions': elem_descriptions,  # do we even need this?
        'matrix_results': matrix_results,
        'redis_wait_key': redis_waitkey,
        'expected_result_key': redis_resultkey,
        'relevant_comparisons': relevant_comparisons
    }

    # _push_amqp_msg(queue_name, json.dumps(msg))
    _push_redis_msg(queue_name, json.dumps(msg))

    print('waiting for SimMatrixResult (key: %s)' % redis_waitkey)
    redis_client = SimMatrixRedisClient(host=REDIS_HOSTNAME, port=REDIS_PORT)
    redis__wait_for_key(redis_waitkey, client=redis_client)
    elem_ids, sim_matrix = redis_client.get_sim_matrix(redis_resultkey)
    redis_client.delete_sim_matrix(redis_resultkey)
    print('finished waiting')

    return elem_ids, sim_matrix


async def compute_clusters(**kwargs):

    graph, context = kwargs['graph'], kwargs['graph'].context
    task_node = kwargs['task_node']

    _, predecessors = task_node.get_predecessor_task_nodes()

    visual_sims = predecessors['get_visual_sims'][0].task_result

    existing_descs = context['elem_descs_consolidated']
    elem_ids = [id for id in existing_descs.keys()]
    existing_descs_li = [existing_descs[id] for id in elem_ids]

    matrix_results = await _get_sims(existing_descs_li, context)
    matrix_results['visually_similar'] = visual_sims

    elem_ids, sim_matrix = await trio.to_thread.run_sync(
        request_sim_matrix, existing_descs_li, matrix_results, context
    )

    cluster_objects, _, leftover_ids = get_clusters_dbscan(
        sim_matrix, existing_descs_li, eps=0.407
    )

    #from webextractor.pipeline_new2.drawing import draw_clusters_on_driver
    #await draw_clusters_on_driver(graph.driver, cluster_objects)

    await _save_cluster_data(
        graph.ws_cli, graph.cluster_task_model_uid,
        existing_descs, cluster_objects
    )

    return cluster_objects


async def _save_cluster_data(websocket_client, task_uid, elem_descs, cluster_objects):

    def _create_descs_for_vue(descs_dict):
        descs = {}
        for node_id, ed in descs_dict.items():
            ed_vue = {}
            for key in VUEJS_DESC_FIELDS:
                ed_vue[key] = ed[key]
            descs[node_id] = ed_vue
        return descs

    await websocket_client.send({
        'view': 'update_object',
        'model': 'ClusterTask', 'uid': task_uid,
        'fields': {
            'listpageElementsById': _create_descs_for_vue(elem_descs),
            'listpageLinkClusters': {
                c.uid: c.node_ids for c in cluster_objects
            }
        }
    })

    _, json_url = await trio.to_thread.run_sync(
        s3_json_upload, 'listpage-link-elements', elem_descs
    )

    # _, json_url = s3_json_upload(
    #    'listpage-link-elements', elem_descs
    # )

    await websocket_client.send({
        'view': 'update_object',
        'model': 'ClusterTask', 'uid': task_uid,
        'fields': {'__listpageLinkClustersS3Url': json_url}
    })


async def actions_daemon(**kwargs):

    graph, redis_cli = kwargs['graph'], kwargs['graph'].redis_cli
    _, predecessors = kwargs['task_node'].get_predecessor_task_nodes()

    cluster_objects = predecessors['compute_clusters'][0].task_result
    action_queue = 'actions-%s' % graph.cluster_task_model_uid

    while True:
        # wait and respond to user actions
        print('awaiting action on queue: %s' % action_queue)
        msg = await redis_cli.queue_pop(action_queue)
        print('action received')
        msg_dict = json.loads(msg)
        action = msg_dict['action']

        if action == 'elemsSelected':
            await action__elemsSelected(
                graph.ws_cli, graph.cluster_task_model_uid, graph.context['elem_descs_consolidated'],
                msg_dict['data']['chosenElemIds']
            )

        import pdb; pdb.set_trace()
        print()


async def action__elemsSelected(ws_cli, ct_model_uid, elem_descs, chosen_elem_ids):

    chosen_cluster_elems = [elem_descs[id] for id in chosen_elem_ids]

    # get detailpage columns
    detailpage_urls = [ed['url'] for ed in chosen_cluster_elems if ed.get('url')][:3]  # limit number for now
    if len(detailpage_urls) < 2:
        await ws_cli.send({
            'view': 'proxy_action',
            'uid': ct_model_uid,
            'model': 'ClusterTask',
            'action': 'reportError',
            'data': {
                'message': 'failed to fetch 2 or more HTML pages'
            }
        })
        return

    tup = find_detailpage_columns(detailpage_urls)
    dp_columns, page_data, canvas_screenshot_fp, page_ss_width = tup
    await _save_detailpage_column_data(
        ws_cli, ct_model_uid, detailpage_urls, canvas_screenshot_fp, dp_columns
    )


async def _save_detailpage_column_data(ws_cli, ct_model_uid, detailpage_urls, canvas_screenshot_fp, columns):

    # todo: make async
    def _get_image_data_bytes(image_fp):
        with open(image_fp, "rb") as image_file:
            bytes = image_file.read()
            bytes_encoded = pickle_dumps_str(bytes)
            return bytes_encoded
    import pdb; pdb.set_trace()
    descs_by_id = {}
    column_clusters = {}

    for col in columns:
        col_ids = []
        for elem in col.elems:
            if elem is None:
                col_ids.append(None)
                continue
            uid = uuid.uuid4().hex
            descs_by_id[uid] = {'rect': elem.rect_scaled, 'text': elem.text, 'node_id': uid}
            col_ids.append(uid)
        column_clusters[uuid.uuid4().hex] = col_ids

    canvas_img_data = _get_image_data_bytes(canvas_screenshot_fp)

    print('updating websocket with column data')
    await ws_cli.send({
        'view': 'update_object',
        'model': 'ClusterTask', 'uid': ct_model_uid,
        'fields': {
            'detailpage_column_clusters': column_clusters,
            'detailpage_table_elements_by_id': descs_by_id,
            'detailpage_canvas_image_data': canvas_img_data,
        }
    })


async def create_graph__analyze_page(nursery, redis_cli, cluster_task_model_uid, page_url):

    FUNCTIONS = {
        'launch_driver': launch_driver,
        'get_outer_html_and_ancestors': get_outer_html_and_ancestors,
        'resize_browser': resize_browser,
        'check_for_new_elems_after_resize': check_for_new_elems_after_resize,
        'get_xpaths': get_xpaths,
        'get_screenshot_data': get_screenshot_data,
        'get_rect_multiple': get_rect_multiple,
        'get_computed_css_multiple': get_computed_css_multiple,
        'consolidate_descs': consolidate_descs,
        'consolidate_descs2': consolidate_descs2,
        'get_display_multiple': get_display_multiple,
        'get_featureset_multiple': get_featureset_multiple,
        'get_visual_sims': get_visual_sims,
        'compute_clusters': compute_clusters,
        'actions_daemon': actions_daemon
    }
    WORKER_LOOPS = [
        TaskGraph.WorkerLoop('default', 1, None),  # todo: fill in this list
        TaskGraph.WorkerLoop('driver_loop', 1, [
            'launch_driver', 'get_outer_html_and_ancestors', 'resize_browser'
        ])
    ]

    graph = TaskGraph(FUNCTIONS, WORKER_LOOPS)

    graph.cluster_task_model_uid = cluster_task_model_uid
    graph.redis_cli = redis_cli
    graph.ws_cli = TrioWebSocketClient()
    await graph.ws_cli.connect(nursery, '127.0.0.1', WEBSOCKET_PORT)

    ld_task = await graph.create_task(
        'launch_driver', ((cluster_task_model_uid, page_url), {}), None
    )
    get_outers_task1 = await graph.create_task(
        'get_outer_html_and_ancestors', None, [ld_task.uid]
    )
    resize_task = await graph.create_task(
        'resize_browser', None, [ld_task.uid]
    )
    check_new_elems_task = await graph.create_task(
        'check_for_new_elems_after_resize', None, [resize_task.uid]
    )
    xpaths_task = await graph.create_task(
        'get_xpaths', None, [get_outers_task1.uid, check_new_elems_task.uid]
    )

    screenshot_task = await graph.create_task(
        'get_screenshot_data', None, [xpaths_task.uid]
    )
    rects_task = await graph.create_task(
        'get_rect_multiple', None, [xpaths_task.uid]
    )
    css_task = await graph.create_task(
        'get_computed_css_multiple', None, [xpaths_task.uid]
    )
    display_task = await graph.create_task(
        'get_display_multiple', None, [css_task.uid]
    )

    consolidate_task = await graph.create_task(
        'consolidate_descs', None, [
            get_outers_task1.uid, check_new_elems_task.uid, xpaths_task.uid,
            rects_task.uid, css_task.uid, display_task.uid
        ]
    )

    visual_sims_task = await graph.create_task(
        'get_visual_sims', None, [screenshot_task.uid, consolidate_task.uid]
    )

    featureset_task = await graph.create_task(
        'get_featureset_multiple', None, [consolidate_task.uid]
    )

    consolidate_task2 = await graph.create_task(
        'consolidate_descs2', None, [featureset_task.uid]
    )

    cluster_task = await graph.create_task(
        'compute_clusters', None, [
            consolidate_task2.uid, visual_sims_task.uid
        ]
    )

    actions_daemon_task = await graph.create_task(
        'actions_daemon', None, [cluster_task.uid]
    )

    '''   
    display_data = get_display_multiple(
        coll.elems, coll.descs_by_id
    )
    process_batch(coll, coll.elem_ids, 'display', display_data, context)
    feature_sets = get_featureset_multiple(
        coll.elem_ids, coll.descs_by_id
    )
    process_batch(
        coll, coll.elem_ids, 'feature_set', feature_sets, context
    )    
    '''
    # wait_condition = GenericSchedulingCondition(
    #    graph, 'COMPLETE__ALL', word_count__task_uids)
    # await graph.create_task(
    #    'combine_page_word_counts', None, [wait_condition.uid])
    return graph


class ClusterTask(WsRedisModel):
    fields = (
        ('uid', str),
        ('pageUrl', str),

        ('screenshotUrl', str),
        ('screenshotHeight', int),

        ('listpageClusteringProgress', list),

        ('listpageLinkClusters', dict),
        ('__listpageLinkClustersS3Url', str),

        ('chosenElemIds', list),

        ('listpageTextClusters', dict),
        ('listpageElementsById', dict),

        ('detailpage_canvas_image_url', str),
        ('detailpage_column_clusters', dict),
        ('detailpage_elements_by_id', dict)
    )

    @classmethod
    async def post_create_handler(cls, uid, fields, ws_context):
        print('ClusterTask.post_create_handler() called')

        msg = {'task_uid': uid, 'page_url': fields['page_url']}

        redis_client = ws_context['redis_client']
        await redis_client.lpush('clustering_pipeline', json.dumps(msg))

        # _push_redis_msg('clustering_pipeline', msg)
        # msg = {'task_uid': uid, 'page_url': fields['page_url']}
        # await amqp_basic_publish('clustering_pipeline', msg)

    @classmethod
    async def proxy_action(cls, uid, action, action_payload_data, ws_context):
        redis_client = ws_context['redis_client']
        subscribers = ws_context['notifier'].subscribers_by_model_uid[uid]

        if action == 'elemsSelected':
            action_queue = 'actions-%s' % uid
            msg = {'action': action, 'data': action_payload_data}
            print('proxy_action: pushing to queue: %s' % action_queue)
            await redis_client.lpush(action_queue, json.dumps(msg))
        elif action == 'reportError':
            msg = {
                'uid': uid,
                'message_type': 'error',
                'message': action_payload_data['message']
            }
            for ws in subscribers:
                if ws.closed is None:
                    await ws.send_message(msg)


'''
        await ws_cli.send({
            'view': 'proxy_action',
            'uid': ct_model_uid,
            'model': 'ClusterTask',
            'action': 'reportError'
            'data': {
                'message': 'failed to fetch 2 or more HTML pages'
            }
        })

'''


async def main():

    ws_models = {'ClusterTask': ClusterTask}

    async with TrioRedisClient(addr=REDIS_HOSTNAME.encode(), port=REDIS_PORT) as redis_cli:
        async with trio.open_nursery() as nursery:

            # run a websocket server for the ClusterTask data model
            nursery.start_soon(
                start_ws_model_server, '0.0.0.0', WEBSOCKET_PORT, ws_models, nursery
            )

            # get messages from 'clustering_pipeline', signals that a ClusterTask was created
            while True:
                msg = await redis_cli.queue_pop('clustering_pipeline')
                msg = json.loads(msg)
                nursery.start_soon(
                    analyze_page, nursery, msg['task_uid'], msg['page_url']
                )


async def analyze_page(nursery, cluster_task_model_uid, page_url):
    print('analyzing page: %s' % page_url)
    async with TrioRedisClient(addr=REDIS_HOSTNAME.encode(), port=REDIS_PORT) as redis_cli:
        graph = await create_graph__analyze_page(
            nursery, redis_cli, cluster_task_model_uid, page_url
        )
        await execute_graph(graph, 15)
        # graph.draw()


'''
async def main():

    task_uid = None
    page_url = 'https://www.theregister.com/'  #'https://soas.ac.uk/about'  #  #

    graph = await create_graph__analyze_page(task_uid, page_url)

    await execute_graph(graph, 15)

    graph.draw()
'''


if __name__ == '__main__':
    trio.run(main)


# consider using this for neural network inference:
# https://github.com/tensorflow/serving
