

def areas_similar(ld1, ld2, context):

    width1 = ld1['rect']['width']
    height1 = ld1['rect']['height']
    width2 = ld2['rect']['width']
    height2 = ld2['rect']['height']

    if (width1, height1) == (width2, height2):
        return 0

    if height1 == height2:
        if abs(width1 - width2) <= 6:
            return 0

    if (width1, height1) == (0, 0) and (width2, height2) != (0, 0):
        return 1
    if (width2, height2) == (0, 0) and (width1, height1) != (0, 0):
        return 1
    
    if width1 == 0 or width2 == 0:
        if width1 == width2:
            return 0
        return 1

    if height1 == 0 or height2 == 0:
        if height1 == height2:
            return 0
        return 1
    
    area1, area2 = ld1['rect']['area'], ld2['rect']['area']
    rect1, rect2 = ld1['rect'], ld2['rect']

    if area1 == 0 and area2 == 0:
        return 0.22  # area 0 but height or width is different

    if (area1 == 0 and area2 > 0) or (area2 == 0 and area1 > 0):
        return 1
    if area1 < 50 and area2 < 50:
        return 0.5

    ratio = max(area1, area2) / min(area1, area2)
    if ratio > 3:  # too large
        return 1

    width_similar = abs(rect1['width'] - rect2['width']) < 4
    height_similar = abs(rect1['height'] - rect2['height']) < 4

    if width_similar and ratio < 1.5:
        return 0
    if height_similar and ratio < 1.5:
        return 0

    if width_similar and ratio < 2:
        return 0.28
    if height_similar and ratio < 2:
        return 0.28

    if ratio < 1.25:  # (and neither heights nor widths are similar
        return 0.5

    return 1
