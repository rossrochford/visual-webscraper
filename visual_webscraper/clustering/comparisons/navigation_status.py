
HEADER_THRESH = 550


def compare_navigation_status(ld1, ld2, context):
    nav_ids = context['nav_elem_ids']  # ids of elements identified as navigation elements

    id1, id2 = ld1['node_id'], ld2['node_id']

    if id1 not in nav_ids and id2 not in nav_ids:
        return 0.5

    if (id1 in nav_ids and id2 not in nav_ids) or (id2 in nav_ids and id1 not in nav_ids):
        # one is navigation and the other is not
        return 1

    assert(id1 in nav_ids and id2 in nav_ids)

    return 0
