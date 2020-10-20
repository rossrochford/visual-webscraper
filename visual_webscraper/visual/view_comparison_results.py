import json
import sys
import random
from uuid import uuid4
#import dataset
import time
import os
import numpy as np

from PIL import Image
from flask import Flask, request, Response, send_file, redirect
from jinja2 import Template

#from util import create_rect, visual_similarity__compare_links, get_pairs, SAME_THRESH, DIFF_THRESH
#from image_rect import UNSURE


def image_view(image_path):
    if image_path.startswith('file://'):
        image_path = image_path.split('file://')[1]
    if '//' in image_path:
        image_path = image_path.replace('//', '/')
    if not image_path.startswith('/'):  # let's not support relative paths for simplicity
        image_path = '/' + image_path

    if os.path.exists(image_path) is False and image_path.startswith('/Users/rossrochford'):
        filename = image_path[image_path.rfind('/') + 1:]
        image_path = os.path.join(os.environ['IMAGE_SIM_TEST_DATA'], 'images', filename)

    return send_file(image_path, mimetype='image/png')


def summary():
    ans = 's'
    if request.args.get('ans'):
        ans = request.args['ans']

    pairs = get_pairs(ans)

    rects = {}
    for img1, img2 in pairs:
        if img1 not in rects:
            rects[img1] = create_rect(img1)
        if img2 not in rects:
            rects[img2] = create_rect(img2)

    correct_count, incorrect_count, unsure_count = 0, 0, 0
    #html_list = []
    entries = []
    for (img1, img2) in pairs:
        r1, r2 = rects[img1], rects[img2]
        img1 = '/image' + img1
        img2 = '/image' + img2
        sim_val = visual_similarity__compare_links(r1, r2)

        if (sim_val < SAME_THRESH and ans == 's') or (sim_val > DIFF_THRESH and ans == 'd'):
            eval_ans = 'CORRECT'
            correct_count += 1
        elif (sim_val < SAME_THRESH and ans == 'd') or (sim_val > DIFF_THRESH and ans == 's'):
            eval_ans = 'INCORRECT'
            incorrect_count += 1
        else:
            eval_ans = 'UNSURE'
            unsure_count += 1

        filename1 = img1[img1.rfind('/')+1:img1.rfind('.')-1]
        filename2 = img2[img2.rfind('/') + 1:img2.rfind('.') - 1]

        entries.append({
            'img1': img1, 'img2': img2, 'sim': str(sim_val)[:6], 'result': ans.upper(), 'uid': (filename1+filename2)
        })

    context = {
        'entries': entries,
        'correct': correct_count,
        'incorrect': incorrect_count,
        'unsure': unsure_count
    }
    template = Template(open('visual_matrix_new/testing/view_data.html').read())
    html = template.render(context)

    return Response(html)


def show_performance():
    ans = 's'
    if request.args.get('ans'):
        ans = request.args['ans']

    pairs = get_pairs(ans)

    rects = {}
    for img1, img2 in pairs:
        if img1 not in rects:
            rects[img1] = create_rect(img1)
        if img2 not in rects:
            rects[img2] = create_rect(img2)

    entries = []

    for (img1, img2) in pairs:
        r1, r2 = rects[img1], rects[img2]
        img1 = '/image' + img1
        img2 = '/image' + img2
        sim_val = visual_similarity__compare_links(r1, r2)

        if (ans == 's' and sim_val < SAME_THRESH) or (ans == 'd' and sim_val > DIFF_THRESH):
            entries.append({
                'img1': img1, 'img2': img2, 'sim': str(sim_val)[:6],
            })

    context = {'entries': entries}
    template = Template(open('visual_matrix_new/testing/view_data.html').read())
    html = template.render(context)
    return Response(html)



IMG_DIR = '/home/ross/code/events_project/webextractor/webextractor/visual/test_images'


from os.path import join as join_path
import json


def create_summary_html():
    json_dict = json.loads(
        open(join_path(IMG_DIR, 'image_sims.json')).read()
    )
    similar_image_pairs = []
    different_image_pairs = []
    ambiguous_image_pairs = []

    for key, sims in json_dict['similarities'].items():
        i, j = key.split('__')
        i, j = i, j
        try:
            img_fp1 = json_dict['images'][i]
            img_fp2 = json_dict['images'][j]
        except:
            import pdb; pdb.set_trace()

        colour_sim, structural_sim = sims

        row = {
            'image1': 'file://' + img_fp1,
            'image2': 'file://' + img_fp2,
            'colour_sim': colour_sim,
            'structural_sim': structural_sim
        }

        if colour_sim < 0.25 or (structural_sim and structural_sim < 0.3):
            similar_image_pairs.append(row)
        elif colour_sim > 0.33 or (structural_sim and structural_sim > 0.33):  #if sims[0] > 0.33 or sims[1] > 0.33:
            different_image_pairs.append(row)
        else:
            ambiguous_image_pairs.append(row)

    def rank(di):
        return di['colour_sim'], not (di['structural_sim'] is None)

    similar_image_pairs.sort(key=rank)
    different_image_pairs.sort(key=rank)
    ambiguous_image_pairs.sort(key=rank)

    context = {
        'similar_images': similar_image_pairs,
        'different_images': different_image_pairs,
        'ambiguous_images': ambiguous_image_pairs
    }
    template = Template(open('/home/ross/code/events_project/webextractor/webextractor/visual/view_comparison_results.html').read())
    html = template.render(context)

    output_file = open(join_path(IMG_DIR, 'result.html'), 'w')
    output_file.write(html)
    output_file.close()

import dataset
from PIL import Image


def get_db_data():
    TEST_DATA_DIR = '/home/ross/code/events_project_extras/visual_matrix_new__test_data'  # os.environ['IMAGE_SIM_TEST_DATA']

    DB_FILEPATH = os.path.join(TEST_DATA_DIR, 'ImageSim.db')
    IMG_DIR = join_path(TEST_DATA_DIR, 'images')

    #SESSION_DIR = '/Users/rossrochford/code/events_project/clustering_eval/clustering_eval/test_images/'

    db = dataset.connect('sqlite:///' + DB_FILEPATH)
    answers_table = db['answers']

    same = answers_table.find(ans='s', _limit=1000)
    different = answers_table.find(ans='d', _limit=1000)

    for di in same:
        img1 = join_path(IMG_DIR, di['image1'].rsplit('/', 1)[1])
        img2 = join_path(IMG_DIR, di['image2'].rsplit('/', 1)[1])

        Image.open(img1).show()
        Image.open(img2).show()
        import pdb; pdb.set_trace()


if __name__ == '__main__':
    get_db_data()
    #create_summary_html()


'''
if __name__ == '__main__':
    app = Flask(__name__)
    summary = app.route('/summary', methods=['GET'])(summary2)
    #show_performance = app.route('/show_performance', methods=['GET'])(show_performance)

    image_view = app.route('/image/<path:image_path>')(image_view)
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
'''