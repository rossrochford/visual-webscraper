import datetime
import json
import time
import unittest
import shutil

from util_core.util.file_util import get_files_in_dir
from webextractor.selenium_wrapper.main import FirefoxDriverWrapper
from webextractor.visual.main import get_visual_similarities
from webextractor.visual.quantize import quantize_image


TEST_DIR = '/home/ross/code/events_project/webextractor/webextractor/clustering/tests/test_data/'


class TestVisuallySimilar(unittest.TestCase):

    def test_visually_similar(self):

        for fp in get_files_in_dir(TEST_DIR):
            if not fp.endswith('.json'):
                continue
            di = json.loads(open(fp).read())
            elem_descriptions = di['elem_descriptions']
            screenshot_data = {
                'screenshot_fp': fp.replace('.json', '.png'),
                'screenshotQ_fp': fp.replace('.json', '-or8.png')
            }
            bf = datetime.datetime.now()
            get_visual_similarities(elem_descriptions, screenshot_data)
            af = datetime.datetime.now()
            print('time: %s' % (af-bf).total_seconds())


if __name__ == '__main__':
    unittest.main()
