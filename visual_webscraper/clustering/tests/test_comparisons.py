from collections import defaultdict
import json
from os import environ
import time
import unittest
import uuid

import pika

from util_core.util.file_util import get_files_in_dir
from webextractor.clustering.comparisons.featureset_overlap import featureset_overlap
from webextractor.clustering.comparisons.content import compare_content
from webextractor.clustering.comparisons.is_visible import compare_visibility
from webextractor.clustering.comparisons.spatial_alignment import spatially_aligned
from webextractor.clustering.comparisons.url_similarity import url_similarity
#from webextractor.clustering.comparisons.visual_similarity import visually_similar
from webextractor.clustering.comparisons.area_similarity import areas_similar
from webextractor.clustering.comparisons.area_alignment import area_alignment_simple
from webextractor.clustering.comparisons.euclidean_distance import (
    adjusted_euclidean_distance, standard_euclidean_distance
)
from webextractor.clustering.comparisons.computed_styles import (
    compare_computed_styles, compare_computed_styles_jaccard
)

AMQP_URL = environ['CELERY_BROKER_URL']
PIKA_PARAMS = pika.connection.URLParameters(AMQP_URL)

QUEUE_NAME = 'sim_matrix_worker_rust'

COMPARISON_FUNCTIONS = [
    adjusted_euclidean_distance,
    area_alignment_simple,
    areas_similar,
    compare_computed_styles,
    #compare_computed_styles_jaccard,
    compare_content,
    #compare_navigation_status,
    compare_visibility,
    featureset_overlap,
    spatially_aligned,
    #standard_euclidean_distance,
    url_similarity,
    #visually_similar
]

TEST_DIR = '/home/ross/code/events_project/webextractor/webextractor/clustering/tests/test_data'

DATA_TYPES = [
    'area',
    'computed_styles',
    'content',
    'feature_set',
    'url',
    'visibility',
]


def get_matrix_results__python(elem_descriptions, context):

    elem_descriptions = elem_descriptions[:150]

    matrix_results = {}

    for func in COMPARISON_FUNCTIONS:
        sims = []
        for i, ed1 in enumerate(elem_descriptions):
            for j, ed2 in enumerate(elem_descriptions):
                if i >= j:
                    continue
                sims.append(
                    func(ed1, ed2, context)
                )
        matrix_results[func.__name__] = sims

    return matrix_results


def get_matrix_results__rust(elem_descriptions, context):

    rabbitmq_connection = pika.BlockingConnection(PIKA_PARAMS)
    uid = uuid.uuid4().hex

    elem_descriptions = elem_descriptions.copy()
    elem_descriptions = elem_descriptions[:150]
    # for ed in elem_descriptions:
    #     del ed['ancestor_path']
    context['quick'] = False

    for dt in DATA_TYPES:
        msg = {
            'data_type': dt,
            'pipeline_session_uid': uid,
            'elem_descriptions': elem_descriptions,
            'context': context,
            'do_flush': False
        }

        rabbitmq_connection.channel().basic_publish(
            exchange='', body=json.dumps(msg).encode(),
            routing_key=QUEUE_NAME
        )

    msg = {
        'data_type': '',
        'pipeline_session_uid': uid,
        'elem_descriptions': [],
        'context': context,
        'do_flush': True,
    }

    rabbitmq_connection.channel().basic_publish(
        exchange='', body=json.dumps(msg).encode(),
        routing_key=QUEUE_NAME
    )
    time.sleep(10)
    fp = '/tmp/%s.json' % uid
    matrix_results = json.loads(open(fp).read())
    return matrix_results


class TestComparisons(unittest.TestCase):

    def test_comparisons(self):
        for fp in get_files_in_dir(TEST_DIR):
            di = json.loads(open(fp).read())
            context = di['context']
            elem_descriptions = di['elem_descriptions']
            print('elem_descriptions len: %s' % len(elem_descriptions))
            # matrix_results = get_matrix_results(elem_descriptions, context)
            matrix_results1 = get_matrix_results__rust(elem_descriptions, context)
            matrix_results2 = get_matrix_results__python(elem_descriptions, context)

            num_discrepancies = defaultdict(int)
            for k in matrix_results1.keys():
                for i in range(11175):
                    if abs(matrix_results1[k][i] - matrix_results2[k][i]) > 0.035:
                        num_discrepancies[k] += 1

            import pdb; pdb.set_trace()
            print()
            break


if __name__ == '__main__':
    unittest.main()
