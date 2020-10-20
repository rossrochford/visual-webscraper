import datetime

from webextractor.element_descriptions.util import add_hashes, add_computed_style_weights, calculate_computed_style_weights
from webextractor.element_descriptions.descriptions import LinkElemDescription


def _is_invisible(ld):
    spatial_vis = ld['spatial_visibility']
    if spatial_vis == 'OUTSIDE_PAGE' or spatial_vis.endswith('__ZERO_AREA') or ld['jquery__is_hidden']:
        print('spatial_visibility: '+spatial_vis)
        return True
    import pdb; pdb.set_trace()
    return False


def get_link_descriptions(driver, context, link_elems=None):

    start = datetime.datetime.now()
    filter_invisible = context.get('filter_invisible', False)

    if link_elems is None:
        link_elems = driver.link_elements

    link_descriptions = []
    num_invisible = 0

    print('get_link_descriptions(): TODO: add bs4_elems (then remove before json saving)')

    for i, link_elem in enumerate(link_elems):
        desc = LinkElemDescription(link_elem, i, context)
        ld = desc.to_dict()
        ld['index_original'] = i
        if filter_invisible and _is_invisible(ld):
            num_invisible += 1
            continue
        link_descriptions.append(ld)

    if filter_invisible:
        # fix misaligned index values
        for i, ld in enumerate(link_descriptions):
            ld['index'] = i

    end = datetime.datetime.now()
    print('time getting link descriptions: %s' % (end-start))

    add_hashes(link_descriptions)

    print('WARNING: very_common_features disabled')
    #context['very_common_features'] = find_common_features(link_descriptions)
    context['computed_style_weights'] = calculate_computed_style_weights(
        link_descriptions
    )
    add_computed_style_weights(link_descriptions, context)

    # if 'container_info' in keys:  todo: temporarily removing this
    #     container_info = get_container_info(driver, link_elems)
    #     add_container_data(link_descriptions, container_info)

    print('WARNING: GridFinderWithIndex disabled')
    #GridFinderWithIndex(driver, link_descriptions).add_neighbour_data()

    return link_descriptions
