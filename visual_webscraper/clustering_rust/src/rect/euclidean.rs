use super::super::descs;


static INFLECTION: f32 = 800.0;

static MAX_WIDTH: f32 = 1300.0;
static MAX_HEIGHT: f32 = 2500.0;


static MAX_DIST: f32 = 2817.8;  // ((MAX_WIDTH).powf(2.0)) + ((MAX_HEIGHT).powf(2.0)).sqrt();


pub fn adjusted_euclidean_distance(rect1: &descs::RectDesc, rect2: &descs::RectDesc, context: &descs::Context) -> f32 {

    let y_diff = (rect1.y - rect2.y).abs();
    let mut scaled_y_diff = y_diff;
    if scaled_y_diff > INFLECTION {
        scaled_y_diff = &INFLECTION + ((scaled_y_diff - &INFLECTION) / 2.0);
        scaled_y_diff = scaled_y_diff.min(MAX_HEIGHT);
    }

    let mut x_diff = (rect1.x - rect2.x).abs();
    x_diff = x_diff.min(MAX_WIDTH);

    let mut euc_dist_scaled = (
        x_diff.powf(2.0) + scaled_y_diff.powf(2.0)
    ).sqrt();

    if euc_dist_scaled < 170.0 {
        return 0.5;  // too close
    }
    // scale to between 0 and 1
    euc_dist_scaled = euc_dist_scaled.min(MAX_DIST) / (MAX_DIST);

    if context.page_height > 1400 && _are_opposite_ends_of_page(rect1.y, rect2.y, context.page_heightF) {
        euc_dist_scaled = euc_dist_scaled * 1.2;
        euc_dist_scaled = euc_dist_scaled.min(1.0);
    } else if y_diff < 1400.0 && ((rect1.x - rect2.x).abs() < 5.0 || (rect1.y - rect2.y).abs() < 5.0) {
        // if horizontally or vertically aligned
        euc_dist_scaled = euc_dist_scaled * 0.7;
    }

    return euc_dist_scaled;
}

fn _are_opposite_ends_of_page(y1: f32, y2: f32, page_height: f32) -> bool {

    if y1 < 450.0 && page_height - y2 < 450.0 {
        return true;
    }
    if y2 < 450.0 && (&page_height - y1) < 450.0 {
        return true;
    }
    return false;
}
