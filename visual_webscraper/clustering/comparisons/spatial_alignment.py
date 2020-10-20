

def spatially_aligned(ld1, ld2, context):
    rect1 = ld1['rect']
    rect2 = ld2['rect']
    x1, y1 = rect1['x'], rect1['y']
    x2, y2 = rect2['x'], rect2['y']
    x_diff = abs(rect1['x'] - rect2['x'])
    y_diff = abs(rect1['y'] - rect2['y'])

    if x1 == 0 and y1 == 0 and (x2 != 0 or y2 != 0):
        return 0.5
    if x2 == 0 and y2 == 0 and (x1 != 0 or y1 != 0):
        return 0.5

    if abs(x1-x2) < 8 and abs(y1-y2) < 8:
        return 0.5

    if x_diff < 4:
        if y_diff < 3:
            # unusual circumstance, two links have almost the same location
            return 0.5
        if y_diff < 800:
            return 0
        else:
            # disregard aligned pairs that are too far apart
            return 0.5

    if y_diff < 4:
        if x_diff < 3:
            # unusual circumstance, two links have almost the same location
            return 0.5
        if x_diff < 900:
            return 0
        else:
            # disregard aligned pairs that are too far apart
            return 0.5

    if x_diff > 6 or y_diff > 6:
        return 1
    import pdb; pdb.set_trace()
    return 0.5
