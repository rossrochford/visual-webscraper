

'''

def visually_similar(ld1, ld2, context):

    img_rect1, img_rect2 = ld1['img_rect'], ld2['img_rect']

    if not img_rect1.is_comparable(img_rect2):
        return UNSURE, 1 # or should we output 1?  or we could evaluate visual similarity but change the same/different thresholds

    return img_rect1.compare(img_rect2)  # todo: <-- weights are all set to 1 in here (as of Feb 1st 217)

'''

'''
def _compare_is_photo(ld1, ld2, context):

    if ld1['is_photo'] and ld2['is_photo']:
        width_diff = abs(ld1['width'] - ld2['width'])
        height_diff = abs(ld1['height'] - ld2['height'])

        if width_diff < 5 and height_diff < 5:
            return 0
        if width_diff < 5 or height_diff < 5:
            return 0.25
        return 0.33

    if ld1['is_photo'] or ld2['is_photo']:
        return 1

    return None
'''

'''

comparison calculations:
------------------------

hist_difference()
hist_intersection()
compare_summaries()
num_misses()

'''


def visually_similar(ld1, ld2, context):

    # should we check another attribute e.g. jquery__hidden?
    is_displayed1, is_displayed2 = ld1['driver__is_displayed'], ld2['driver__is_displayed']

    if is_displayed1 is False or is_displayed2 is False:
        return 0.5

    img_rect1, img_rect2 = ld1['img_rect'], ld2['img_rect']

    return img_rect1.compare(img_rect2)
