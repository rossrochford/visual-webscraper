use super::descs;


pub fn compare_visibility(ed1: &descs::VisibilityDesc, ed2: &descs::VisibilityDesc, context: &descs::Context) -> f32 {

    if ed1.visibility__ALL_VISIBLE && ed2.visibility__ALL_VISIBLE {
        return 0.5;
    }

    let mut signals: [f32; 5] = [0.0; 5];

    signals[0] = compare_css_computed_visibility(&ed1, &ed2, &context);
    signals[1] = compare_css_is_hidden(&ed1, &ed2, &context);
    signals[2] = compare_css_display(&ed1, &ed2, &context);
    signals[3] = compare_is_displayed(&ed1, &ed2, &context);
    signals[4] = compare_spatial_visibility(&ed1, &ed2, &context);

    /*
    let mut signals = Vec::with_capacity(5);
    signals.push(compare_css_computed_visibility(&ed1, &ed2, &context));
    signals.push(compare_css_is_hidden(&ed1, &ed2, &context));
    signals.push(compare_css_display(&ed1, &ed2, &context));
    signals.push(compare_is_displayed(&ed1, &ed2, &context));
    signals.push(compare_spatial_visibility(&ed1, &ed2, &context));
    */

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


fn compare_spatial_visibility(ed1: &descs::VisibilityDesc, ed2: &descs::VisibilityDesc, context: &descs::Context) -> f32 {

    if ed1.spatial_visibility == ed2.spatial_visibility {
        if ed1.spatial_visibility != "IN_PAGE" {
            return 0.0;
        }
        return -1.0;
    }

    if ed1.spatial_visibility == "IN_PAGE" || ed2.spatial_visibility == "IN_PAGE" {
        return 1.0;
    }

    return -1.0;
}

fn compare_is_displayed(ed1: &descs::VisibilityDesc, ed2: &descs::VisibilityDesc, context: &descs::Context) -> f32 {
    if ed1.driver__is_displayed == ed2.driver__is_displayed {
        if ! ed1.driver__is_displayed {
            return 0.0;
        }
        return -1.0;
    }

    return 1.0;
}

fn compare_css_display(ed1: &descs::VisibilityDesc, ed2: &descs::VisibilityDesc, context: &descs::Context) -> f32 {
    if ed1.cssComputed__display == ed2.cssComputed__display {
        return 0.0;
    }
    return 1.0;
}

fn compare_css_is_hidden(ed1: &descs::VisibilityDesc, ed2: &descs::VisibilityDesc, context: &descs::Context) -> f32 {
    if ed1.jquery__is_hidden == ed2.jquery__is_hidden {
        if ed1.jquery__is_hidden {
            return 0.0;
        }
        return -1.0;
    }
    return 1.0;
}

fn compare_css_computed_visibility(ed1: &descs::VisibilityDesc, ed2: &descs::VisibilityDesc, context: &descs::Context) -> f32 {
    if ed1.cssComputed__visibility == ed2.cssComputed__visibility {
        if ed1.cssComputed__visibility == "visible" {
            return -1.0;
        }
        return 0.0;
    }
    return 1.0;
}
