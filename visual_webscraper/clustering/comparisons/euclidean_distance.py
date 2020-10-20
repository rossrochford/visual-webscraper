
import math

INFLECTION = 800

MAX_WIDTH = 1300
MAX_HEIGHT = 2500

MAX_DIST = math.sqrt(
    ((MAX_WIDTH)**2) + ((MAX_HEIGHT)**2)
)


def _are_opposite_ends_of_page(y1, y2, page_height):
    if y1 < 450 and page_height - y2 < 450:
        return True
    if y2 < 450 and page_height - y1 < 450:
        return True
    return False


def adjusted_euclidean_distance(ld1, ld2, context):

    x1, y1 = ld1['rect']['x'], ld1['rect']['y']
    x2, y2 = ld2['rect']['x'], ld2['rect']['y']

    # euc_dist_orig = math.sqrt(
    #     ((x2-x1)**2) + ((y2-y1)**2)
    # )
    page_height = context['page_height']

    scaled_height_diff = height_diff = abs(y2-y1)
    if scaled_height_diff > INFLECTION:
        scaled_height_diff = INFLECTION + ((scaled_height_diff-INFLECTION) / 2)
        scaled_height_diff = min(MAX_HEIGHT, scaled_height_diff)

    width_diff = min(MAX_WIDTH, abs(x2-x1))  # cap height and width at 2500 and 1300

    euc_dist_scaled = math.sqrt(
        (width_diff**2) + (scaled_height_diff**2)
    )

    if euc_dist_scaled < 170:
        # too close
        return 0.5

    # scale to between 0 and 1
    euc_dist_scaled = min(MAX_DIST, euc_dist_scaled) / MAX_DIST

    if page_height > 1400 and _are_opposite_ends_of_page(y1, y2, page_height):
        euc_dist_scaled *= 1.2
        euc_dist_scaled = min(1, euc_dist_scaled)
    elif height_diff < 1400 and (abs(x2-x1) < 5 or abs(y2-y1) < 5):
        # if horizontally or vertically aligned
        euc_dist_scaled *= 0.7

    return euc_dist_scaled


def standard_euclidean_distance(ld1, ld2, context):

    x1, y1 = ld1['rect']['x'], ld2['rect']['y']
    x2, y2 = ld1['rect']['x'], ld2['rect']['y']

    width_diff = min(MAX_WIDTH, abs(x2-x1))  # cap height and width at 2500 and 1300
    height_diff = min(MAX_HEIGHT, abs(y2-y1))

    dist = math.sqrt(
        (width_diff**2) + (height_diff**2)
    )

    return dist / MAX_DIST
