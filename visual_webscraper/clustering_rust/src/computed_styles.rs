use super::descs;

static NUM_KEYS: usize = 134;

static MINUS_ONE: i32 = -1;


pub fn compare_computed_styles(ed1: &descs::ComputedStylesDesc, ed2: &descs::ComputedStylesDesc, context: &descs::Context) -> f32 {

    let mut num_equal = ed1.all_computed_styles__array_int.iter().zip(ed2.all_computed_styles__array_int.iter()).filter(|&(a, b)| a == b).count();
    let num_unequal = NUM_KEYS - num_equal;

    for it in ed1.all_computed_styles__array_int.iter().zip(ed2.all_computed_styles__array_int.iter()) {
        let (a, b) = it;
        if *a == MINUS_ONE && *b == MINUS_ONE {
            num_equal -= 1;
        }
        /*
        if a.len() == 0 && b.len() == 0 {
            num_equal -= 1;
        }*/
    }

    let mut val = (-1.0 * (num_unequal as f32)) + ((num_equal as f32) * 0.5);
    let _v = val.min(13.0);
    val = _v.max(-16.0);

    if val == -16.0 {
        return 1.0;
    }
    return 1.0 - ((val + 16.0) / 29.0);
}
