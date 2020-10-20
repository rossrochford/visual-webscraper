use super::descs;

use std::os::raw::c_char;
use std::os::raw::c_int;
use std::ffi::{CString, CStr};

extern crate unicode_segmentation; // 1.2.1
extern crate strsim;

use strsim::{normalized_levenshtein};  // or: levenshtein

use std::collections::HashMap;

//use std::collections::HashSet;

use unicode_segmentation::UnicodeSegmentation;


extern {
    fn simil (a: *const c_char, b: *const c_char) -> c_int;
    //fn isimil (a: *const c_char, b: *const c_char) -> c_int;
}


pub fn compare_content(ed1: &descs::ContentDesc, ed2: &descs::ContentDesc, context: &descs::Context) -> f32 {

    let mut signals = Vec::with_capacity(4);

    signals.push(compare_text(&ed1, &ed2, &context));
    signals.push(compare_start_tag(&ed1, &ed2, &context));
    signals.push(compare_img(&ed1, &ed2, &context));
    // NOTE: this is very slow
    signals.push(compare_outer_sim(&ed1, &ed2, &context));

    signals.retain(|&x| x >= -0.05);  // should be: x != -1.0 but this is safer

    if signals.len() == 0 {
        return 0.5;
    }
    let sum: f32 = signals.iter().sum();
    return sum / (signals.len() as f32);
}


fn compare_text(ed1: &descs::ContentDesc, ed2: &descs::ContentDesc, context: &descs::Context) -> f32 {

    if ed1.text.len() == 0 && ed2.text.len() == 0 {
        return -1.0;
    }

    if ed1.text == ed2.text {
        return 0.0;
    }

    if ed1.text.len() == 0 || ed2.text.len() == 0 {
        return 1.0;
    }

    if ed1.text_is_more_link && ed2.text_is_more_link {
        return 0.0;
    } else if ed1.text_is_more_link || ed2.text_is_more_link {
        return 1.0;
    }

    if ed1.text_is_digit && ed2.text_is_digit {
        if ed1.text.len() == ed2.text.len() {
            return 0.0;
        }
        return 0.15;
    }

    if ed1.text_has_date.len() > 0 && ed2.text_has_date.len() > 0 {
        if ed1.text_has_date == ed2.text_has_date {
            return 0.0;
        }
        return 0.35;
    }
    else if ed1.text_has_date.len() > 0 || ed2.text_has_date.len() > 0 {
        return 1.0;
    }

    return -1.0;
}


fn string_distance_full(ed1: &descs::ContentDesc, ed2: &descs::ContentDesc, context: &descs::Context) -> f32 {

    let mut sim_val1: f32 = 0.0;
    unsafe {
        sim_val1 = simil(ed1.outer_html_no_content_for_sim.as_ptr(), ed2.outer_html_no_content_for_sim.as_ptr()) as f32;
    }

    sim_val1 = 1.0 - (sim_val1 / 100.0);

    if context.quick {
        return sim_val1;
    }

    if sim_val1 < 0.3 {
        return sim_val1;
    }

    let mut sim_val2: f32 = 0.0;
    unsafe {
        sim_val2 = simil(ed1.outer_html_no_content_rev_for_sim.as_ptr(), ed2.outer_html_no_content_rev_for_sim.as_ptr()) as f32;
    }

    sim_val2 = 1.0 - (sim_val2 / 100.0);

    if (sim_val1 - sim_val2).abs() <= 0.19 {
        return (sim_val1 + sim_val2) / 2.0;
    }

    // todo: test that this is similar to editdistance.eval() in python (note: normalisation will be different)
    let mut edit_dist = normalized_levenshtein(&ed1.outer_html_no_content, &ed2.outer_html_no_content) as f32;
    edit_dist = 1.0 - edit_dist;

    let mut val = ((edit_dist * 0.34) + (sim_val1 * 0.33) + (sim_val2 * 0.33)) as f32;
    if val < 0.15 {
        val = (val * 0.6) + (sim_val1.min(sim_val2) * 0.4);
    } else if val > 0.85 {
        val = (val * 0.6) + (sim_val1.max(sim_val2) * 0.4);
    }

    return val;
}


pub fn simil_quick<'a>(str1: *const c_char, str2: *const c_char) -> f32 {
    // based on difflib.SequenceMatcher().quick()

    /*
        CStr represents a borrowed reference to a nul-terminated array of bytes. It can
        be constructed safely from a &[u8] slice, or unsafely from a raw *const c_char. It can
        then be converted to a Rust &str by performing UTF-8 validation, or into an owned CString.

        &CStr is to CString as &str is to String: the former in each pair are borrowed references;
        the latter are owned strings.
    */
    let mut bcount: HashMap<c_char, i32> = HashMap::new();

    let mut len1 = 0;
    let mut len2 = 0;
    unsafe {
        len1 = CStr::from_ptr(str1).to_bytes().len();
        len2 = CStr::from_ptr(str2).to_bytes().len();
    }

    let length = (len1 + len2) as f32;

    if length == 0.0  {
        return 0.0;  // both length zero
    }

    for i in 0..len2 {
        let mut ch: c_char = 0 as c_char;
        unsafe {
            //let ch = (str2.offset(i) as str);
            ch = *(str2.offset(i as isize));
        }
        bcount.entry(ch).or_insert(0);
        *bcount.get_mut(&ch).unwrap() += 1;
    }

    let mut avail: HashMap<c_char, i32> = HashMap::new();
    let mut matches: i32 = 0;
    for i in 0..len1 {
        let mut elt = 0 as c_char;
        unsafe {
            elt = *(str1.offset(i as isize));
        }
        // let elt = str1[i];
        let mut numb = 0;
        if avail.contains_key(&elt) {
            numb = avail[&elt];
        } else if bcount.contains_key(&elt) {
            numb = bcount[&elt];
        }
        avail.entry(elt).or_insert(0);
        *avail.get_mut(&elt).unwrap() = numb - 1;

        if numb > 0 {
            matches = matches + 1;
        }
    }

    let val = (2.0 * (matches as f32)) / length;
    return 1.0 - val;
    // calculate_ratio
    //let val = (2.0 * (matches as f32)) / ((len1 + len2) as f32);
    //return 1.0 - val;
}

/*
    return _calculate_ratio(matches, len(str1) + len(str2))


def real_quick_ratio(str1, str2):
    la, lb = len(str1), len(str2)
    return _calculate_ratio(min(la, lb), la + lb)


def _calculate_ratio(matches, length):
    if length:
        return 2.0 * matches / length
    return 1.0

*/

/*
fn simil_upperbound<'a>(str1: String, str2: String) -> f32 {
    let mut bcount: HashMap<String, i32> = HashMap::new();
    for ch in str2.graphemes(true) {
        bcount.entry(String::from(ch)).or_insert(0);
        *bcount.get_mut(ch).unwrap() += 1;
    }

    let mut avail: HashMap<String, i32> = HashMap::new();
    let mut matches: i32 = 0;
    for elt in str1.graphemes(true) {
        let mut numb = 0;
        if avail.contains_key(elt) {
            numb = avail[elt];
        } else if bcount.contains_key(elt) {
            numb = bcount[elt];
        }
        *avail.get_mut(elt).unwrap() = numb - 1;
        if numb > 0 {
            matches = matches + 1;
        }
    }
    // calculate_ratio
    let len_denom = str1.len() + str2.len();
    return (2.0 * (matches as f32)) / (len_denom as f32);
}
*/

fn compare_outer_sim(ed1: &descs::ContentDesc, ed2: &descs::ContentDesc, context: &descs::Context) -> f32 {

    if ed1.parent_tag_name != ed2.parent_tag_name && ed1.tag_name != ed2.tag_name {
        return 1.0;
    }

    if context.quick {
        let quick_sim = simil_quick(
            ed1.outer_html_no_content_for_sim.as_ptr(),
            ed2.outer_html_no_content_for_sim.as_ptr()
        );
        if quick_sim > 0.57 {
            return quick_sim;
        }
        // todo: also parent outer?
    }

    if ed1.parent_outer_html_no_content.len() > 1 && ed2.parent_outer_html_no_content.len() > 1 {
        let max_len = ed1.parent_outer_html_no_content.len().max(ed2.parent_outer_html_no_content.len()) as f32;
        if max_len > 450.0 {
            let min_len = ed1.parent_outer_html_no_content.len().min(ed2.parent_outer_html_no_content.len()) as f32;
            if max_len / min_len > 3.0 {
                return 1.0;
            }
        }
        unsafe {
            let mut parent_outer_sim: f32 = simil(
                ed1.parent_outer_for_sim.as_ptr(),  // can assume these are not None here
                ed2.parent_outer_for_sim.as_ptr()
            ) as f32;
            parent_outer_sim = 1.0 - (parent_outer_sim / 100.0);
            if parent_outer_sim < 0.11 {
                return 0.0;
            }
        }
    }

    if (ed1.num_tags > 2 && ed2.num_tags > 2) || (ed1.outer_html_no_content.len() > 160 && ed2.outer_html_no_content.len() > 160) {
        let outer_sim = string_distance_full(&ed1, &ed2, &context);
        if outer_sim < 0.1 {
            return 0.0;
        }
        if outer_sim > 0.85 {
            return 1.0;
        }
    }

    return -1.0;
}


fn compare_img(ed1: &descs::ContentDesc, ed2: &descs::ContentDesc, context: &descs::Context) -> f32 {

    if ed1.img_type.len() > 0 || ed2.img_type.len() > 0 {
        let ans = (ed1.img_type != ed2.img_type) as i32;
        return ans as f32;
    }

    if ed1.parent_img_type.len() > 0 || ed2.parent_img_type.len() > 0 {
        let p_ans = (ed1.parent_img_type != ed2.parent_img_type) as i32;
        return p_ans as f32;
    }

    return -1.0;
}


fn compare_start_tag(ed1: &descs::ContentDesc, ed2: &descs::ContentDesc, context: &descs::Context) -> f32 {
    let start_tag1 = &ed1.start_tag;
    let start_tag2 = &ed2.start_tag;

    if start_tag1 == start_tag2 && start_tag1.len() > 24 {
        return 0.0;
    }

    if ed1.parent_start_tag == ed2.parent_start_tag {
        if start_tag1 == start_tag2 {
            return 0.0;
        }
        return 0.25;
    }

    return -1.0;  // or could use Option return value and return None
}