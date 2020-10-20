use super::descs;


pub fn url_similarity(ed1: &descs::UrlDesc, ed2: &descs::UrlDesc, context: &descs::Context) -> f32 {

    if ed1.url.len() == 0 || ed2.url.len() == 0 {
        if ed1.url == ed2.url {
            return 0.0;
        }
        return 1.0;
    }

    if ed1.url == ed2.url {
        return 0.0;
    }

    let signal0 = compare_url_type(&ed1, &ed2, &context);
    if signal0 == 1.0 {
        return 1.0;  // mismatching types
    }

    let mut signals: [f32; 3] = [0.0; 3];
    signals[0] = signal0;
    signals[1] = compare_url_type2(&ed1, &ed2, &context);
    signals[2] = compare_hosts(&ed1, &ed2, &context);

    let mut num_signals: i32 = 0;
    let mut signal_sum: f32 = 0.0;

    for &val in signals.iter() {
        if val >= 0.0 {
            num_signals += 1;
            signal_sum += val;
        }
    }

    if num_signals == 0 {
        return 0.5;
    }

    return signal_sum / (num_signals as f32);
}

/*

cdef double url_similarity(UrlObject ld1, UrlObject ld2, Context context):

    if len(ld1.url) == 0 or len(ld2.url) == 0:
        if ld1.url == ld2.url:
            return 0
        return 1

    if ld1.url == ld2.url:
        return 0

    cdef double[:] signals = np.zeros((3,))

    signals[0] = _compare_url_type(ld1, ld2, context)
    if signals[0] == 1:
        return 1  # mismatching url types

    signals[1] = _compare_url_type2(ld1, ld2, context)
    signals[2] = _compare_hosts(ld1, ld2, context)

    cdef int num_signals = 0
    cdef double signal_sum = 0

    for val in signals:
        if val >= 0:
            num_signals += 1
            signal_sum += val

    if num_signals == 0:
        return 0.5

    return signal_sum / num_signals

*/

fn compare_hosts(ed1: &descs::UrlDesc, ed2: &descs::UrlDesc, context: &descs::Context) -> f32 {

    let url_host1 = &ed1.url_host;
    let url_host2 = &ed2.url_host;
    let page_url_host = &context.page_url_host;

    if url_host1 == url_host2 {
        if url_host1 == page_url_host {
            // very common so we'll only give a small
            // signal (ideally we would vary the weight rather than magnitude)
            return 0.3;
        }
        return 0.0;
    } else {  // url_host1 != url_host2
        if url_host1 == page_url_host || url_host2 == page_url_host {
            return 1.0;
        }
        return 0.5;
    }
}


fn compare_url_type(ed1: &descs::UrlDesc, ed2: &descs::UrlDesc, context: &descs::Context) -> f32 {

    if ed1.url_type == ed2.url_type {
        if ed1.url_type == "WEBPAGE" {
            return -1.0;
        }
        return 0.0;
    }

    if ed1.url_type == "WEBPAGE" || ed2.url_type == "WEBPAGE" {
        return 1.0;
    }
    return -1.0;
}


fn compare_url_type2(ed1: &descs::UrlDesc, ed2: &descs::UrlDesc, context: &descs::Context) -> f32 {

    let is_gmap1 = ed1.url__is_google_map;
    let is_eb1 = ed1.url__is_eventbrite_event;
    let is_gcal1 = ed1.url__google_calendar;
    let is_social1 = ed1.url__is_social;
    let contains_event1 = ed1.url__contains_event;

    let is_gmap2 = ed2.url__is_google_map;
    let is_eb2 = ed2.url__is_eventbrite_event;
    let is_gcal2 = ed2.url__google_calendar;
    let is_social2 = ed2.url__is_social;
    let contains_event2 = ed2.url__contains_event;

    if is_gmap1 && is_gmap2 {
        return 0.0;
    } else if is_gmap1 || is_gmap2 {
        return 1.0;
    }

    if is_eb1 && is_eb2 {
        return 0.0;
    } else if is_eb1 || is_eb2 {
        return 1.0;
    }

    if is_gcal1 && is_gcal2 {
        return 0.0;
    } else if is_gcal1 || is_gcal2 {
        return 1.0;
    }

    if is_social1 && is_social2 {
        return 0.0;
    } else if is_social1 || is_social2 {
        return 1.0;
    }

    if contains_event1 && contains_event2 {
        return 0.0;
    } else if contains_event1 || contains_event2 {
        return 1.0;
    }

    return -1.0;
}


/*

cdef double _compare_hosts(UrlObject ld1, UrlObject ld2, Context context):

    url_host1 = ld1.url_host
    url_host2 = ld2.url_host
    cdef string page_url_host = context.page_url_host

    if url_host1 == url_host2:
        if url_host1 == page_url_host:
            # very common so we'll only give a small signal (ideally we would vary the weight rather than magnitude)
            return 0.3
        return 0

    else:  # url_host1 != url_host2
        if url_host1 == page_url_host or url_host2 == page_url_host:
            return 1
        return 0.5


cdef double _compare_url_type(UrlObject ld1, UrlObject ld2, Context context):

    if ld1.url_type == ld2.url_type:
        if ld1.url_type == WEBPAGE:
            return -1
        return 0

    if ld1.url_type == WEBPAGE or  ld2.url_type == WEBPAGE:
        return 1

    return -1


cdef double _compare_url_type2(UrlObject ld1, UrlObject ld2, Context context):

    is_gmap1, is_gmap2 = ld1.url__is_google_map, ld2.url__is_google_map
    is_eb1, is_eb2 = ld1.url__is_eventbrite_event, ld2.url__is_eventbrite_event
    is_gcal1, is_gcal2 = ld1.url__google_calendar, ld2.url__google_calendar
    is_social1, is_social2 = ld1.url__is_social, ld2.url__is_social

    contains_event1 = ld1.url__contains_event
    contains_event2 = ld2.url__contains_event

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

    return -1

*/