

def area_alignment_simple(ed1, ed2, context):

    rect1, rect2 = ed1['rect'], ed2['rect']

    sides_same = abs(rect1['width']-rect2['width']) <= 2 or abs(rect1['height']-rect2['height']) <= 2
    is_aligned = abs(rect1['y']-rect2['y']) <= 2 or abs(rect1['x']-rect2['x']) <= 2

    if sides_same and is_aligned:
        ans = 0
    elif sides_same or is_aligned:
        ans = 0.25
    else:
        ans = 0.75

    min_area = min(rect1['area'], rect2['area'])
    max_area = max(rect1['area'], rect2['area'])

    areas_different = False
    if max_area > 0:
        areas_different = min_area / max_area < 0.6
    areas_different = areas_different or abs(min_area-max_area) > 1300

    if areas_different:
        ans *= 1.3  # max will be 0.975

    return ans
