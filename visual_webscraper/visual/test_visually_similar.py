from collections import defaultdict
import json

from PIL import Image

from webextractor.visual.extract import create_screenshot_context, get_img_data
from webextractor.visual.compare import _compare_summaries, _hist_difference, _compare_structure, _compare_colours, visually_similar_NEW, visually_similar
from webextractor.visual.quantize import QuantizedScreenshot
from util_core.util.file_util import get_files_in_dir


GT_DIR = '/home/ross/code/events_project/webextractor/webextractor/clustering/ground_truth/data/cluster_data'
SIMILAR_INDEXES_FP = '/home/ross/code/events_project/webextractor/webextractor/clustering/ground_truth/data/visually_similar_clusters.json'

# pairs of same/different items {'same_pairs': uid: [(node_id, node_id)]}}
VISUAL_PAIRS = '/home/ross/code/events_project/webextractor/webextractor/clustering/ground_truth/data/visual_pairs.json'


def get_vals(ed1, ed2, ctx):

    img_data1 = get_img_data(ed1, ctx)
    img_data2 = get_img_data(ed2, ctx)
    if img_data1['dummy'] or img_data2['dummy']:
        return
    val1 = _compare_summaries(img_data1, img_data2)
    val2 = _hist_difference(img_data1, img_data2)
    val3 = _compare_structure(img_data1, img_data2)
    val4 = _compare_colours(img_data1, img_data2)

    return val1, val2, val3, val4


def show_rect(ed, ctx):

    rect = ed['rect']

    box = (
        rect['x'], rect['y'], rect['x'] + rect['width'],
        rect['y'] + rect['height']
    )
    ctx['image'].crop(box).show()


def main():

    from util_core.util.graph import create_histogram

    visual_pairs = json.loads(open(VISUAL_PAIRS).read())

    vals_when_same = []
    vals_when_different = []

    for m, fp in enumerate(get_files_in_dir(GT_DIR)):
        if not fp.endswith('.json'):
            continue
        uid = fp.rsplit('/', 1)[-1].rstrip('.json')

        print('.')
        ground_truth = json.loads(open(fp).read())

        img_fp = fp.replace('.json', '.png')
        imgQ_fp = fp.replace('.json', '_Q.png')

        image = Image.open(img_fp)
        imageQ = QuantizedScreenshot.create(imgQ_fp, quantize=False)

        ctx = create_screenshot_context(image, imageQ)

        descs_by_id = {
            ed['node_id']: ed for ed in ground_truth['results_new']['elem_descriptions']
        }

        if uid not in visual_pairs['same_pairs']:
            continue

        for id1, id2 in visual_pairs['same_pairs'][uid]:
            ed1 = descs_by_id[id1]
            ed2 = descs_by_id[id2]

            img_data1 = get_img_data(ed1, ctx)
            img_data2 = get_img_data(ed2, ctx)
            if img_data1['dummy'] or img_data2['dummy']:
                continue
            vals_when_same.append(
                visually_similar_NEW(img_data1,  img_data2)
            )
            # vals_when_same2.append(
            #     visually_similar(img_data1, img_data2)
            # )

        if uid not in visual_pairs['different_pairs']:
            continue

        for id1, id2 in visual_pairs['different_pairs'][uid]:
            ed1 = descs_by_id[id1]
            ed2 = descs_by_id[id2]

            img_data1 = get_img_data(ed1, ctx)
            img_data2 = get_img_data(ed2, ctx)
            if img_data1['dummy'] or img_data2['dummy']:
                continue
            vals_when_different.append(
                visually_similar_NEW(img_data1, img_data2)
            )
            # vals_when_different2.append(
            #     visually_similar(img_data1, img_data2)
            # )

    create_histogram(vals_when_same)
    #create_histogram(vals_when_same2)

    create_histogram(vals_when_different)
    #create_histogram(vals_when_different2)


def mainOLD():
    from util_core.util.graph import create_histogram
    similar_indexes = json.loads(open(SIMILAR_INDEXES_FP).read())

    vals_diff = []
    vals_same = []
    exceptions = defaultdict(list)

    same_pairs = defaultdict(list)
    different_pairs = defaultdict(list)

    incorrectly_different = {'7a1f424188b35eb249e2494f9ba2a0c7': [(2, 3)], 'b2eb27ba403a8f0629a2f63201125825': [], 'c04c913fdbad198563aa49785f2bab95': [(1, 0)], '76e4fc7c22ad301da82741a2f5387a2f': [(0, 1), (0, 5), (1, 3), (3, 0), (5, 3)], 'c4c31d656ad6f4055071d3dc5ab485fc': [], '792c5da92205ac8191ac2da11107a576': [(3, 2)], '1ff892ef29f9008b597a2e4b0b009b9a': [(0, 2)], '5c723d00ed50ededd326b4e74926cd10': [(0, 1), (0, 3), (0, 5), (1, 3), (1, 5), (3, 5)], '000c70a1446d7758393193223ce93a08': [(2, 0)], 'ff89e1e2efb0333912727fff33cb7698': [(1, 2), (1, 3), (2, 3)], '87755ce20e65d13b0231e88bc33cdf2b': [], '3ae03095442a4ee3592342f2b7dac525': [], 'cdb1a16947371b2b97ce38d50e3fc233': [(0, 4), (1, 4)], 'f23ef3ce80d891fed6c15b51c5d4bf27': [], 'a80f8e33e91b61b3cc219d9d7686ae58': [], '96b2ca9b8d41b1703a6dbe5d25c1b922': [(0, 2), (0, 3), (1, 3)], '403a7b7ee4f68745a3fd193d3cabac49': [(0, 1)], 'e09ab6cd7634fe2f3c7c566f2562b541': [(0, 5), (1, 0)], '190f9b0734c86db36bca347c8fa25a56': [], '52b0b88531f96c614bbe69a1931d9ed9': [(2, 3)], 'e7c8b2815f5f2bc5495f4169a4de83c8': [(2, 3)], 'c22fa413af2eeb92b744c15abab44a2f': [], '4284d186bb615e64923948713b1c32d7': [], 'd959a796b74b4e4f34895afab4d1b86a': [], '0cfb5d954d4c5f7e9578169327817911': [], '38731648c88c85ed5c002ed15f97d73c': [(4, 5)], 'f0518ad6066d1c521d335cb96b48c87a': [(0, 5), (2, 4)], 'a1df0d0d100b9a1343eff14c2a9dfac5': [], '7eec0509eeec95582a0b5823e39728d3': [(1, 3), (2, 1), (2, 3)], 'b41fff37483995965dce1b4f3916f0a1': [(2, 3)], '56b042e074f2e40b715a75ff67856a44': [(0, 1)], '904556c339f3e40000960caed1049e5d': [], '75da9f2b1ccfa81e9dbee712cecfd4ab': [(3, 2)], '27f0e7e5f1034c3fcbc54c7249e6010b': [], '3766bd52af5d0ded27d72f47fc709aea': [], 'bcc685bfda53357dcc198c5c16eac8df': [], 'f133f059b25e359b0186c7bd11f08632': [], '9094e6f10ef85360f527e77fb2a76ecb': [], '63721ebccd8ad80ba83b360348a0c10a': [], '2a2d808db180f728bd4beb4df4637858': [(0, 2)], '73ffb0579827944a7f6ef799e0020ded': [(1, 2)], '50b323cdb73ea3b38e16d8dc2c991df0': [], 'c20553164f83005a14e31ec860a3cf49': [(1, 2)], '1c5eb2dff79837da8526598d526d715d': [], 'f805489b10c61edc77b657c49fa91727': [(2, 1)], '55266e310b42ec3d615fc83fd7895af1': [], '1c4f00bdf2da2ce0e840e1b1d224977e': [(1, 2)], '827ebf9d537747aa0228bb6448a9aabd': [], 'f4dff7bdf9e461c9eb8a4ccc6d3d8380': [(0, 2)], 'c04642092baaef3510c677d1b462968a': [], '40df4dd1e7eac62843568b4186f7be89': [(1, 2), (1, 4), (2, 4)], '8db1505a63463601c7c673207b720821': [], 'e4f02350b26d841df5c50dfad4efd179': [], '68fcba64c953cfbdf67d825dabd371a8': [], 'e42f69b5270e09ab175dd237eef4a022': [(4, 3)], 'db1c6d45d3e6a73623c4141c46594b36': [(1, 4)], 'f6c2d5c42d82dd92eaca2b5d9cc7069c': [(1, 3)], '35c7f592134c8c911f7adf5368170f56': [(0, 1)], '4e1ff45787d099a9c9fe00dd78a2e7f3': [], '07bfc2f6552b67d286d1106c1c1eaaa4': [], 'e955bfd60e68fa942df8d0ac2c783dd4': [], '69447b6b7ec82059ae81a4ea727b9843': [], 'e9171e24d013800b571c9d89eae2f1f2': []}

    for m, fp in enumerate(get_files_in_dir(GT_DIR)):
        if not fp.endswith('.json'):
            continue
        uid = fp.rsplit('/', 1)[-1].rstrip('.json')

        if uid not in similar_indexes or len(similar_indexes[uid]) < 2:
            continue
        print('.')
        ground_truth = json.loads(open(fp).read())

        img_fp = fp.replace('.json', '.png')
        imgQ_fp = fp.replace('.json', '_Q.png')

        image = Image.open(img_fp)
        imageQ = QuantizedScreenshot.create(imgQ_fp, quantize=False)

        ctx = create_screenshot_context(image, imageQ)

        descs_by_id = {
            ed['node_id']: ed for ed in ground_truth['results_new']['elem_descriptions']
        }
        cluster_ids = ground_truth['cluster_ids']
        clusters = []
        for index in similar_indexes[uid]:
            clusters.append(
                [descs_by_id[id] for id in cluster_ids[index]]
            )

        for i, cluster1 in enumerate(clusters):
            for ed1 in cluster1:
                for ed2 in cluster1:
                    if ed1['node_id'] == ed2['node_id']:
                        continue
                    vals_same.append(get_vals(ed1, ed2, ctx))

                    id1, id2 = ed1['node_id'], ed2['node_id']
                    same_pairs[uid].append(
                        (id1, id2)
                    )

            for j, cluster2 in enumerate(clusters):
                if i == j:
                    continue
                if (i, j) in incorrectly_different[uid] or (j, i) in incorrectly_different[uid]:
                    continue

                #vals_diff_curr = []
                for ed1 in cluster1:
                    for ed2 in cluster2:
                        different_pairs[uid].append(
                            (ed1['node_id'], ed2['node_id'])
                        )
                        vals_diff.append(get_vals(ed1, ed2, ctx))
                        #vals_diff_curr.append(vals_diff[-1])

                '''
                if (i, j) in exceptions[uid] or (j, i) in exceptions[uid]:
                    continue
                simvals = [tup[0] for tup in vals_diff_curr if tup is not None]
                if simvals:
                    avg_summary_sim = np.mean(simvals)
                    if avg_summary_sim < 0.5:
                        show_rect(cluster1[0], ctx)
                        show_rect(cluster2[0], ctx)

                        # pairs of clusters too similar to be considered different
                        confirm = input('exception? y/n').strip()
                        if confirm == 'y':
                            exceptions[uid].append((i, j))'''

    vals_same = [tup for tup in vals_same if tup is not None]
    vals_diff = [tup for tup in vals_diff if tup is not None]

    for i in range(4):
        vals1 = [tup[i] for tup in vals_same if tup[i] is not None]
        vals2 = [tup[i] for tup in vals_diff if tup[i] is not None]
        create_histogram(vals1)
        create_histogram(vals2)
        import pdb; pdb.set_trace()


# close all images
# for pid in $(ps aux | grep 'display ' | awk "{print $2}"); do kill -9 $pid; done

if __name__ == '__main__':
    main()
