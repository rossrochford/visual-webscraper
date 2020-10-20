import base64
from collections import defaultdict
import re
import uuid

from PIL import Image, ImageDraw
import requests

import urllib
import urllib.parse

import numpy as np
from rtree import index

from util_core.util.draw import COLOURS_ALL
from util_core.ocr.ocr_util import TesseractOCR
from util_core.util.html_util import remove_html_content, get_start_tag, get_tags
from util_core.util.string_util import string_distance_simple

MAX_TAGS = 8

SPLASH_HOST = 'http://localhost:8050'
SPLASH_PS_QUERY = '/render.html?resource_timeout=15&wait=3&url='
SPLASH_PD_QUERY = "/execute?timeout=25&wait=1&lua_source="

SPLASH_START_COMMAND = 'docker rm -f splashnode; docker run -d -p 8050:8050 --name splashnode scrapinghub/splash --max-timeout 650'

GET_PAGE_DATA_REDUCED = """
function main(splash)

    local get_text_elements = splash:jsfunc([[
        function () {

            var results = new Array();  // maybe also add <nav> ?
            var tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'div', 'span', 'p', 'abbr', 'article', 'li', 'strong', 'section', 'header', 'summary', 'time', 'footer', 'i', 'b', 'em', 'td'];
            
            for(var i=0; i < tags.length; i++){
                var elements = document.getElementsByTagName(tags[i]);

                for(var j=0; j < elements.length; j++){
                    var elem = elements[j];
                    var html = elements[j].outerHTML; 
                    //if(html.length < 3)
                        //continue;

                    var num_tags = html.length - html.replace(/</g, '').length;
                    if ( num_tags > 12) {
                        continue
                    }
                    
                    var parent_outer_html;
                    if ( num_tags < 3 ) {
                        parent_outer_html = elem.parentNode.outerHTML;
                    } else {
                        parent_outer_html = null;
                    }
                    var di = {
                        "outer_html": html, "tag": tags[i],
                        "rect": elem.getBoundingClientRect(), 
                        "parent_outer_html": parent_outer_html, 
                        "num_tags": num_tags,
                        //"computed_styles": getComputedStyle(elem),
                    }; 

                    results.push(di);
                }
            }
            return results;
        }
    ]])

    response = splash:http_get{"%(url)s", follow_redirects=true}
    if string.find(response.headers["Content-Type"], "text/html") == nil then
        return {error = "unexpected content-type"}
    end

    splash:set_viewport_size(1300, 2000)
    splash:go("%(url)s")
    splash:wait(1.3)

    page_source = splash:html()

    local di = {
        text_elements = get_text_elements(),
        page_source = page_source,
        screenshot = splash:png()
    }
    return di
end
"""


def _is_offline(status_code, html):
    if html is None:
        return True
    if status_code in (500, 501, 502, 503) or '502 Bad Gateway' in html or '503 Service Unavailable' in html:
        return True
    return False


def get_page_data(url):

    code = urllib.parse.quote(GET_PAGE_DATA_REDUCED % {'url': url})
    query_url = SPLASH_HOST + SPLASH_PD_QUERY + code

    resp = requests.get(query_url)

    status = resp.status_code
    resp_body = resp.content.decode()

    if _is_offline(status, resp_body) is False and status == 200:
        return resp.json()

    raise Exception('splash failed')


def pair_search_bounds(elem1, elem2):
    box1 = elem1.search_bounds
    box2 = elem2.search_bounds

    x = min(box1[0], box2[0])
    y = min(box1[1], box2[1])
    end_x = max(box1[2], box2[2])
    end_y = max(box1[3], box2[3])

    return x, y, end_x, end_y


class SplashTextElem(object):

    def __init__(self, pos, di):

        self.rect = di['rect']

        self.rect_scaled = None

        self.rect['x'] = int(round(self.rect['left']))
        self.rect['y'] = int(round(self.rect['top']))

        del self.rect['left']
        del self.rect['top']
        del self.rect['right']
        del self.rect['bottom']

        self.uid = uuid.uuid4().hex
        self.pos = pos
        self.di = di

        di['outer_html_no_content'] = remove_html_content(di['outer_html'])
        if di['parent_outer_html']:
            di['parent_outer_html_no_content'] = remove_html_content(di['parent_outer_html'])

        di['start_tag'] = get_start_tag(di['outer_html'])

        self.matches = []

    def __hash__(self):
        return self.uid

    @property
    def tag_name(self):
        return self.di['tag']

    @property
    def search_bounds(self):
        x = max(0, self.rect['x'] - 30)
        y = max(0, self.rect['y'] - 160)
        end_x = self.rect['x'] + self.rect['width'] + 50
        end_y = self.rect['y'] + self.rect['height'] + 160
        return x, y, end_x, end_y

    def set_scale(self, scale):

        if self.rect_scaled:
            print('warning: set_scale() called twice')
            return

        self.rect_scaled = {
            'x': int(round(self.rect['x'] * scale)),
            'y': int(round(self.rect['y'] * scale)),
            'width': int(round(self.rect['width'] * scale)),
            'height': int(round(self.rect['height'] * scale))
        }

    def add_to_index(self, index):
        box = (
            int(self.rect['x']),
            int(self.rect['y']),
            int(self.rect['x']) + 15,
            int(self.rect['y']) + 15
        )
        try:
            index.insert(self.pos, box, obj=self)
        except:
            import pdb; pdb.set_trace()

    def similarity(self, other):

        if self.tag_name != other.tag_name:
            return 1

        outer_sim = string_distance_simple(
            self.di['outer_html_no_content'],
            other.di['outer_html_no_content']
        )
        if 'parent_outer_html_no_content' in self.di and 'parent_outer_html_no_content' in other.di:
            outer_sim2 = string_distance_simple(
                self.di['parent_outer_html_no_content'],
                other.di['parent_outer_html_no_content']
            )
            outer_sim = (0.65 * outer_sim) + (0.35 * outer_sim2)

        sim = outer_sim

        if abs(self.di['rect']['x'] - other.di['rect']['x']) < 10:
            if abs(self.di['rect']['y'] - other.di['rect']['y']) < 40:
                sim *= 0.85
            else:
                sim *= 0.95

        if abs(self.di['rect']['height'] - other.di['rect']['height']) < 3:
            sim *= 0.9

        if self.di['start_tag'] == other.di['start_tag']:
            sim *= 0.9
        else:
            sim *= 1.1

        return sim

    @property
    def text_elems(self):
        content_fragments = re.findall(r'>([^<>]+?)<', self.di['outer_html'])
        content_fragments = [st.strip() for st in content_fragments if st.strip()]
        return content_fragments

    @property
    def text(self):
        texts = self.text_elems
        if len(texts) == 0:
            return None
        txt = '\n'.join(texts).strip()
        txt = txt.replace('&gt;', '>').replace('&lt;', '<')
        return txt


class Column(object):

    def __init__(self, elem1, elem2):
        self.elems = [elem1, elem2]

    @property
    def min_x(self):
        min_x = 3000
        for elem in self.elems:
            if elem and elem.rect['x'] < min_x:
                min_x = elem.rect['x']
        return min_x

    @property
    def max_x(self):
        max_x = 0
        for elem in self.elems:
            if elem:
                end_x = elem.rect['x'] + elem.rect['width']
                if end_x > max_x:
                    max_x = end_x
        return max_x

    def get_avg_pos(self, page_sources):
        positions = []
        for i, elem in enumerate(self.elems):
            if elem:
                pos = page_sources[i].find(elem.di['outer_html'])
                if pos != -1:
                    positions.append(pos)
        self.avg_pos = np.mean(positions)

    def get_avg_coords(self):
        x_vals, y_vals = [], []
        for elem in self.elems:
            if elem:
                x_vals.append(elem.rect['x'])
                y_vals.append(elem.rect['y'])
        x = np.mean(x_vals)
        y = np.mean(y_vals)
        self.avg_coords = y, x

    def is_redundant(self):
        texts = set()

        text_found = False
        number_found = False

        for e in self.elems:
            if e is None:
                continue
            content_fragments = e.text_elems
            if not content_fragments:
                continue
            text_found = True
            if number_found is False:
                for frag in content_fragments:
                    if re.search(r'\d', frag):
                        number_found = True
            texts.add(tuple(content_fragments))

        if number_found:
            return False

        if len(texts) == 1 or text_found is False:
            return True

        return False


def find_groups(urls, page_data):
    pair_count = 0
    anchor_url = urls[0]
    index2 = page_data[urls[1]]['spatial_index']

    # groups_by_tag = defaultdict(list)
    for elem in page_data[anchor_url]['text_elems']:
        if elem.di['num_tags'] > MAX_TAGS:
            continue
        try:
            matches = index2.intersection(elem.search_bounds, objects=True)
        except Exception as e:
            import pdb; pdb.set_trace()
            return
        matches = [
            m.object for m in matches if m.object.tag_name == elem.tag_name
        ]
        matches = [
            (elem.similarity(other), other) for other in matches
        ]
        for sim, other in matches:
            if sim < 0.24:
                elem.matches.append((sim, other))
                other.matches.append((sim, elem))

                pair_count += 1

    uids_used = []
    pairs = []
    for elem in page_data[anchor_url]['text_elems']:
        if elem.di['num_tags'] > MAX_TAGS or not elem.matches:
            continue

        elem.matches.sort(key=lambda tup: tup[0])
        pairs.append(
            (elem, elem.matches[0][1])
        )
        uids_used.append(elem.uid)
        uids_used.append(elem.matches[0][1].uid)

    for elem in page_data[urls[1]]['text_elems']:
        if elem.di['num_tags'] > MAX_TAGS or len(elem.matches) == 0 or elem.uid in uids_used:
            continue
        elem.matches.sort(key=lambda tup: tup[0])
        pairs.append(
            (elem, elem.matches[0][1])
        )
        uids_used.append(elem.uid)
        uids_used.append(elem.matches[0][1].uid)

    columns = []
    for elem1, elem2 in pairs:
        col = Column(elem1, elem2)
        for url in urls[2:]:
            idx = page_data[url]['spatial_index']

            search_bounds = pair_search_bounds(elem1, elem2)
            matches = [m.object for m in idx.intersection(search_bounds, objects=True)]

            pair_matches = []
            for elem3 in matches:
                if elem3.di['num_tags'] > MAX_TAGS:
                    continue
                if elem3.tag_name != elem1.tag_name:
                    continue
                sim = (elem1.similarity(elem3) + elem2.similarity(elem3)) / 2
                if sim < 0.25:
                    pair_matches.append((sim, elem3))
            if pair_matches:
                pair_matches.sort(key=lambda tup: tup[0])
                col.elems.append(pair_matches[0][1])
            else:
                col.elems.append(None)
        columns.append(col)

    columns = [col for col in columns if not col.is_redundant()]

    # fix widths using OCR data
    for col in columns:
        # NOTE: a more conservative fix would be to only adjust elems
        # where height < 13 & len(text) < 80 i.e. a single-line element
        for i, elem in enumerate(col.elems):
            if elem is not None:
                ocr = page_data[urls[i]]['ocr']
                ocr_locations = ocr.find_ocr_locations(elem)
                if len(ocr_locations) == 1:
                    ocr_width = ocr_locations[0]['width']
                    elem.rect['width'] = ocr_width

    return columns


def _scale_image(filepath, scale):

    img = Image.open(filepath)

    height, width = img.size
    if height > 1800:
        img = img.crop((0, 0, 1800, width))
        height = 1800

    # if x_clip:
    #     img = img.crop((x_clip, 0, 1300 - x_clip, 1800))

    new_height = int(round(height * scale))
    new_width = int(round(width * scale))

    img = img.resize((new_height, new_width))
    img.save(filepath)


def _write_screenhshot_to_file(png_str):

    imgdata = base64.b64decode(png_str)
    filepath = '/tmp/%s.png' % uuid.uuid4().hex

    with open(filepath, 'wb') as f:
        f.write(imgdata)

    return filepath


def _create_canvas_image(urls, page_data, columns):

    img_width = 1300
    #x_clip2 = 60

    for col in columns:
        for page_index, e in enumerate(col.elems):
            if e is None:
                continue
            e.rect_scaled = e.rect
            if page_index == 0 or e.rect is None:
                continue

            offset = img_width * page_index
            e.rect_scaled['x'] = e.rect_scaled['x'] + offset

    canvas_images = [Image.open(page_data[u]['screenshot_fp']) for u in urls[:3]]

    widths, heights = zip(*(i.size for i in canvas_images))
    total_width = sum(widths) #- (x_clip2 * 2 * 3)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in canvas_images:
        w, h = im.size
        # im = im.crop((x_clip2, 0, w - x_clip2, h))
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    if max_height > 1400:
        w = len(canvas_images) * 1300
        new_im = new_im.crop((0, 0, w, 1400))

    filepath = '/tmp/%s.png' % uuid.uuid4().hex
    new_im.save(filepath)

    return filepath, widths[0]


def _create_canvas_imageOLD(urls, page_data, columns):

    #min_x = min(col.min_x for col in columns)
    #max_x = max(col.max_x for col in columns)

    #x_clip, scale, img_width = 50, 0.5, 600

    x_clip, scale, img_width = 0, 0.65, 845

    x_clip2 = 60

    '''
    x_clip, scale, img_width = 0, 0.5, 650
    if min_x > 100 and max_x < 1200:
        x_clip = 120
        scale = 0.6132
        img_width = 650  # (1300 - (2 * x_clip)) * scale
    '''

    for col in columns:
        for page_index, e in enumerate(col.elems):
            if e:
                if e.rect is None:
                    continue
                e.set_scale(scale)
                x = e.rect_scaled['x'] - x_clip2
                x += (img_width - (x_clip2 * 2)) * page_index
                e.rect_scaled['x'] = x

    for url in urls:
        ss_filepath = page_data[url]['screenshot_fp']
        _scale_image(ss_filepath, scale)

    canvas_images = [Image.open(page_data[u]['screenshot_fp']) for u in urls[:3]]

    widths, heights = zip(*(i.size for i in canvas_images))
    total_width = sum(widths) - (x_clip2 * 2 * 3)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in canvas_images:
        w, h = im.size
        im = im.crop((x_clip2, 0, w - x_clip2, h))
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    filepath = '/tmp/%s.png' % uuid.uuid4().hex
    new_im.save(filepath)

    return filepath


def collect_detailpage_data(urls):

    p = index.Property()
    p.dimension = 2

    page_data = {}

    ocr = TesseractOCR(reuse=True)

    for url in urls:

        data = get_page_data(url)

        screenshot_fp = _write_screenhshot_to_file(data['screenshot'])
        text_elems = [
            SplashTextElem(i, di) for (i, di) in enumerate(data['text_elements'])
            if 70 < di['rect']['top'] < 1700
        ]
        spatial_index = index.Index(properties=p)
        for elem in text_elems:
            elem.add_to_index(spatial_index)

        page_data[url] = {
            'screenshot_fp': screenshot_fp,
            'page_source': data['page_source'],
            'text_elems': text_elems,
            'spatial_index': spatial_index,
            'ocr': ocr.do_ocr(screenshot_fp)
        }

    return page_data


def _find_possible_description_elems(splash_elems):

    num_tags = outer.count('</')
    num_words = len(re.findall(r'(\w+?)[,|\.|\s]', outer))
    if num_words > 80:
        ratio = num_words / num_tags


class TextColElem(object):

    def __init__(self, rect, text):
        self.rect = rect

        text = text.replace('&gt;', '>').replace('&lt;', '<')

        self.text = text
        self.rect_scaled = None

    def set_scale(self, scale):

        if self.rect is None:
            return

        if self.rect_scaled:
            print('warning: set_scale() called twice')
            return

        self.rect_scaled = {
            'x': int(round(self.rect['x'] * scale)),
            'y': int(round(self.rect['y'] * scale)),
            'width': int(round(self.rect['width'] * scale)),
            'height': int(round(self.rect['height'] * scale))
        }


class TextColumn(object):

    def __init__(self, urls, col_texts, y_bounds, page_data):
        self.urls = urls
        self.col_texts = col_texts
        self.y_bounds = y_bounds
        self.page_data = page_data

        self.rects = self._get_locations()

        self.elems = []
        for i, url in enumerate(self.urls):
            self.elems.append(
                TextColElem(self.rects[i], col_texts[i])
            )

        self._hash = None

    def __hash__(self):
        if self._hash is None:
            details = []
            for e in self.elems:
                if e and e.rect:
                    rect_tuple = tuple([e.rect[k] for k in ('x', 'y')])
                    details.append(e.text)
                    details.append(rect_tuple)
            self._hash = hash(tuple(details))
        return self._hash

    def _get_locations(self):
        locations = []

        # todo: could collect 'definite' locations to reduce box size for searches

        for i, url in enumerate(self.urls):
            target_words = [w.lower() for w in self.col_texts[i].split(' ')]

            # NOTE: we could also search page_data[url]['text_elems'] by text
            ocr_word_idx = self.page_data[url]['ocr'].spatial_word_idx
            ocr_line_idx = self.page_data[url]['ocr'].spatial_line_idx

            txt = self.col_texts[i].lower()
            box = (0, self.y_bounds[i][0] - 30, 1300, self.y_bounds[i][1] + 30)

            ocr_lines = [m.object for m in ocr_line_idx.intersection(box, objects=True)]
            ocr_lines = [
                l for l in ocr_lines
                if l.text.lower() == txt or l.text.lower()[:len(txt)] == txt
            ]

            if len(ocr_lines) == 1:
                box = ocr_lines[0].bbox.box
                locations.append({
                    'x': box[0], 'y': box[1],
                    'width': box[2]-box[0],
                    'height': box[3]-box[1]
                })
                continue

            ocr_words = [m.object for m in ocr_word_idx.intersection(box, objects=True)]
            ocr_words = [w for w in ocr_words if w.text.lower() in target_words]

            if not ocr_words:
                locations.append(None)
                continue
            if len(target_words) != len(target_words):
                import pdb; pdb.set_trace()
            ocr_words.sort(key=lambda w: w.bbox.box[:2])
            start_pos = ocr_words[0].bbox.box[:2]
            ocr_words.sort(key=lambda w: w.bbox.box[2:])
            end_pos = ocr_words[-1].bbox.box[2:]
            locations.append({
                'x': start_pos[0], 'y': start_pos[1],
                'width': end_pos[0] - start_pos[0],
                'height': end_pos[1] - start_pos[1]
            })
            # locations.append((start_pos[0], start_pos[1], end_pos[0], end_pos[1]))

        if None in locations and locations.count(None) != len(locations):
            pass  # todo: set to average location? maybe only if > 2 were found?

        return locations


def create_text_columns(urls, gap_outers, num_rows, page_data):

    results = {}

    num_cols = set()
    y_bounds = {}

    for row_index, outer, y_range in gap_outers:
        outer = re.sub(r'</?br/?>', '', outer, flags=re.I)

        texts = []
        matches = [m for m in re.finditer(r'</?[a-zA-Z0-9]+', outer)]
        if not matches:
            continue
        prev = matches[0]
        for m in matches[1:]:
            st = outer[prev.start():m.start()]
            bf = st[:st.find('<')].strip()
            af = st[st.rfind('>') + 1:].strip()
            texts.extend([bf, af])
            # parts.append(outer[prev.start():m.start()])
            prev = m

        results[row_index] = texts
        y_bounds[row_index] = y_range
        num_cols.add(len(texts))

    if len(num_cols) != 1:
        return []

    num_cols = [n for n in num_cols]
    if num_cols[0] == 0:
        return []

    num_cols = num_cols[0]

    to_remove = []  # indexes of columns to remove
    for col_index in range(num_cols):
        col_vals = [
            row_vals[col_index] for row_vals in results.values()
            if row_vals[col_index].strip()
        ]
        if not col_vals:
            to_remove.append(col_index)

    for row_index, values in results.items():
        results[row_index] = [
            v for (i, v) in enumerate(values) if i not in to_remove
        ]

    num_cols = num_cols - len(to_remove)
    assert num_cols == len(results[min(results.keys())])  # sanity check

    column_objects = []

    for col_index in range(num_cols):
        col_values = []
        for row_index in range(num_rows):
            if row_index in results:
                col_values.append(results[row_index][col_index])
            else:
                col_values.append(None)
        column_objects.append(
            TextColumn(urls, col_values, y_bounds, page_data)
        )

    return column_objects


def create_text_columns_when_keys_inconsistent(urls, gap_outers, page_data):
    keys = [tup[0] for tup in gap_outers]

    # find prefix
    prev_len = prefix_len = 0
    last_pos = keys[0].rfind('__')
    while True:
        prev_len = prefix_len
        prefix_len = keys[0].find('__', prefix_len+1)
        if prefix_len == -1 or prefix_len >= last_pos:
            break
        prefix_key = keys[0][:prefix_len]
        if not all(k.startswith(prefix_key) for k in keys):
            break
    prefix_len = prev_len
    prefix_key = keys[0][:prefix_len]

    # find suffix
    prev_pos = suffix_pos = len(keys[0])
    suffix_key = ''
    while True:
        prev_pos = suffix_pos
        suffix_pos = keys[0].rfind('__', 0, suffix_pos)
        if suffix_pos in (-1, 0):
            break
        suffix_key = keys[0][suffix_pos:]
        if not all(k.endswith(suffix_key) for k in keys):
            break
    suffix_key = keys[0][prev_pos:].lstrip('__')
    suffix_len = len(suffix_key)

    column_results = []

    if len(prefix_key) > 6 and prefix_key.count('__') > 4:
        num_parts = prefix_key.count('<')
        prefix_key_clipped = prefix_key[:prefix_key.rfind('__')]
        new_row_tuples = []
        for key, row_tuples in gap_outers:
            for row_index, outer, y_bounds in row_tuples:
                tag_positions = [
                    m for m in re.finditer(r'</?[a-zA-Z0-9]+', outer, flags=re.I)
                ]

                prefix_end_pos = tag_positions[num_parts-1].start()
                prefix_outer = outer[:prefix_end_pos]
                new_key = get_outer_key(prefix_outer)  # '__'.join(get_tags(prefix_outer))

                assert new_key == prefix_key_clipped
                new_row_tuples.append(
                    (row_index, prefix_outer, y_bounds)
                )
        text_cols = create_text_columns(urls, new_row_tuples, len(urls), page_data)
        column_results.extend(text_cols)

    if len(suffix_key) > 6 and suffix_key.count('__') > 4:

        num_parts = suffix_key.count('<')
        new_row_tuples = []
        for key, row_tuples in gap_outers:
            for row_index, outer, y_bounds in row_tuples:
                tag_positions = [
                    m for m in re.finditer(r'</?[a-zA-Z0-9]+', outer, flags=re.I)
                ]

                suffix_start_pos = tag_positions[-num_parts].start()
                suffix_outer = outer[suffix_start_pos:]
                new_key = get_outer_key(suffix_outer)  # '__'.join(get_tags(suffix_outer))

                assert new_key == suffix_key
                new_row_tuples.append(
                    (row_index, suffix_outer, y_bounds)
                )
        text_cols = create_text_columns(urls, new_row_tuples, len(urls), page_data)
        column_results.extend(text_cols)

    return column_results


def get_outer_key(outer):
    parts = re.findall(r'</?[a-zA-Z0-9]+', outer)
    # key = '__'.join(get_tags(outer, l=True))
    return '__'.join(parts)


def _find_text_columns(urls, page_sources_li, page_data, columns):

    text_columns = []

    for i in range(1, len(columns)):
        gap_outers = defaultdict(list)

        #tag_key_counts = defaultdict(int)
        prev_col = columns[i-1]
        col = columns[i]
        for row_index in range(len(urls)):
            pg_source = page_sources_li[row_index]
            e1 = prev_col.elems[row_index]
            e2 = col.elems[row_index]
            if e1 and e2:
                pos1 = pg_source.index(e1.di['outer_html'])
                pos2 = pg_source.index(e2.di['outer_html'])
                if pos1 == -1 or pos2 == -1:
                    continue
                else:
                    outer = pg_source[pos1:pos2].strip()
                    key = get_outer_key(outer)
                    y_positions = [e1.rect['y'], e2.rect['y']]
                    y_bounds = (min(y_positions), max(y_positions))
                    gap_outers[key].append((row_index, outer, y_bounds))

        gap_outers = [tup for tup in gap_outers.items()]
        gap_outers.sort(key=lambda tup: len(tup[1]), reverse=True)

        if (len(gap_outers) == 1 and len(gap_outers[0][1]) > 1) or len(gap_outers[0][1]) > 2:
            _text_cols = create_text_columns(urls, gap_outers[0][1], len(urls), page_data)
            text_columns.extend(_text_cols)
        else:
            _text_cols = create_text_columns_when_keys_inconsistent(urls, gap_outers, page_data)
            text_columns.extend(_text_cols)
            continue  # todo: break into sub-sections where the keys are consistent? (e.g. find longest prefix and suffix in keys)

    return text_columns


def find_detailpage_columns(urls):

    page_data = collect_detailpage_data(urls)
    # page_sources, page_data, screenshots, spatial_indices = tup
    # page_sources_li = [page_sources[u] for u in urls]
    page_sources_li = [page_data[u]['page_source'] for u in urls]

    columns = find_groups(urls, page_data)

    for col in columns:
        col.get_avg_pos(page_sources_li)
        col.get_avg_coords()

    columns.sort(key=lambda col: col.avg_pos)
    _text_columns = _find_text_columns(urls, page_sources_li, page_data, columns)

    columns.sort(key=lambda col: col.avg_coords)
    _text_columns2 = _find_text_columns(urls, page_sources_li, page_data, columns)

    cols_by_hash = defaultdict(list)
    for col in _text_columns + _text_columns2:
        cols_by_hash[col.__hash__()].append(col)

    text_columns = [cols[0] for (hsh, cols) in cols_by_hash.items()]
    columns.extend(text_columns)

    canvas_screenshot_fp, page_ss_width = _create_canvas_image(urls, page_data, columns)

    #_show_columns(columns, canvas_screenshot_fp, page_ss_width)

    return columns, page_data, canvas_screenshot_fp, page_ss_width


def _show_columns(columns, ss_filepath, page_ss_width):
    img = Image.open(ss_filepath)
    draw = ImageDraw.Draw(img)

    # driver_size = driver.get_window_size()['width'], driver.page_height
    # image_size = img.width, img.height

    for i, col in enumerate(columns):
        for j, elem in enumerate(col.elems):
            if elem is None or elem.rect is None:
                continue
            rect = elem.rect_scaled
            start_pos = (rect['x'], rect['y'])
            end_pos = (rect['x'] + rect['width'], rect['y'] + rect['height'])
            draw.rectangle(
                (start_pos, end_pos), outline=COLOURS_ALL[i % len(COLOURS_ALL)]
            )
    img.show()


def _show_page_data(page_data, url):
    img = Image.open(page_data[url]['screenshot_fp'])
    draw = ImageDraw.Draw(img)

    for i, text_elem in enumerate(page_data[url]['text_elems']):
        rect = text_elem.rect
        start_pos = (rect['x'], rect['y'])
        end_pos = (rect['x'] + rect['width'], rect['y'] + rect['height'])
        draw.rectangle(
            (start_pos, end_pos), outline=COLOURS_ALL[i % len(COLOURS_ALL)]
        )
    img.show()


TEXTS = [
    'Members events',
    'Past Events',
    'ODI Fridays: Untangling your secret data architecture',
    'Details'
]


if __name__ == '__main__':
    URLS = [
        'https://theodi.org/event/odi-fridays-untangling-your-secret-data-architecture/',
        'https://theodi.org/event/a-very-data-ry-christmas-odi-members-only/',
        'https://theodi.org/event/applying-machine-learning-and-ai-techniques-to-data-manchester/'
    ]
    # page_data = collect_detailpage_data(URLS[:1])
    # fix_elem_widths(page_data)
    # _show_page_data(page_data, URLS[0])
    # exit()

    columns, page_data, canvas_img_fp, page_ss_width = find_detailpage_columns(URLS)
    _show_columns(columns, canvas_img_fp, page_ss_width)
    import pdb; pdb.set_trace()
    print()
