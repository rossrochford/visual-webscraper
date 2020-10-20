import numpy as np


def _compare_hosts(ld1, ld2, context):

    url_host1 = ld1['url_host']
    url_host2 = ld2['url_host']
    page_url_host = context['page_url_host']

    if url_host1 == url_host2:
        if url_host1 == page_url_host:
            # very common so we'll only give a small signal (ideally we would vary the weight rather than magnitude)
            return 0.3
        return 0
    else:
        if url_host1 == page_url_host or url_host2 == page_url_host:
            return 1
        return 0.5


def _compare_type(ld1, ld2, context):

    type1, type2 = ld1['url_type'], ld2['url_type']

    if type1 == type2:
        if type1 == 'WEBPAGE':
            return None
        return 0

    if 'WEBPAGE' in (type1, type2):
        return 1

    return None


def _compare_type2(ld1, ld2, context):

    is_gmap1, is_gmap2 = ld1['url__is_google_map'], ld2['url__is_google_map']
    is_eb1, is_eb2 = ld1['url__is_eventbrite_event'], ld2['url__is_eventbrite_event']
    is_gcal1, is_gcal2 = ld1['url__google_calendar'], ld2['url__google_calendar']
    is_social1, is_social2 = ld1['url__is_social'], ld2['url__is_social']

    contains_event1 = ld1['url__contains_event']
    contains_event2 = ld2['url__contains_event']

    if is_gmap1 and is_gmap2:
        return 0
    elif is_gmap1 or is_gmap2:
        return 1

    if is_eb1 and is_eb2:
        return 0
    elif is_eb1 or is_eb2:
        return 1

    if is_gcal1 and is_gcal2:
        return 0
    elif is_gcal1 or is_gcal2:
        return 1

    if is_social1 and is_social2:
        return 0
    elif is_social1 or is_social2:
        return 1

    if contains_event1 and contains_event2:
        return 0
    elif contains_event1 or contains_event2:
        return 1

    return None


FUNCTIONS = [
    _compare_type,
    _compare_type2,
    _compare_hosts,
]


def url_similarity(ld1, ld2, context):

    if (not ld1.get('url')) or (not ld2.get('url')):
        if ld1.get('url') == ld2.get('url'):
            return 0
        return 1

    if ld1['url'] == ld2['url']:
        return 0

    signals = []
    for func in FUNCTIONS:
        sig = func(ld1, ld2, context)
        if sig == 1 and func.__name__ == '_compare_type':
            return 1  # mismatching url types
        # todo: should we also short circuit if sig == 0 and url_type != WEBPAGE?
        signals.append(sig)

    signals = [val for val in signals if val is not None]

    if len(signals) == 0:
        return 0.5

    return float(np.mean(signals))


'''
('https://www.centreforlondon.org/conference/the-london-conference-2019/', 'https://www.centreforlondon.org/event/civil-society-devolution/')

'''