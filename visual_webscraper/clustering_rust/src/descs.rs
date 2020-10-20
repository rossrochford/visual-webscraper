use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use pyo3::types::PyBool;
use pyo3::types::PyUnicode;
use std::collections::HashSet;
use std::collections::HashMap;

use std::os::raw::c_char;
//use std::os::raw::c_int;
use std::ffi::{CString, CStr};

use super::content;
use super::computed_styles;
use super::feature_set;
use super::rect;
use super::url;
use super::visibility;


#[derive(Clone)]
pub struct Context {
    pub page_url: String,
    pub page_url_host: String,
    pub page_height: i32,
    pub page_heightF: f32,
    pub quick: bool
}

impl Context {
    pub fn create_from_dict(py: &Python, context: HashMap<String,PyObject>) -> Context {

        let page_height = context["page_height"].extract::<i32>(*py).unwrap();
        let page_url = context["page_url"].extract::<String>(*py).unwrap();
        let page_url_host = context["page_url_host"].extract::<String>(*py).unwrap();

        let context_struct: Context = Context {
            page_url: page_url, //&(context["page_url"].extract::<String>(*py).unwrap()),
            page_url_host: page_url_host, // &(context["page_url_host"].extract::<String>(*py).unwrap()),
            page_height: page_height,
            page_heightF: page_height as f32,
            quick: context["quick"].extract::<bool>(*py).unwrap(),
        };
        return context_struct;
    }
}

/*
pub struct Context<'a> {
    pub page_url: &'a str,
    pub page_url_host: &'a str,
    pub page_height: i32,
    pub quick: bool
}*/


pub trait ElemDescription {
    //fn get_node_id(&self) -> String {
    fn compare(&self, other: &Self, context: &Context) -> f32 where Self: Sized {
        return 0.0_f32;
    }
}


// #[derive(Serialize, Deserialize)]
#[pyclass]
pub struct UrlDesc {
    pub node_id: String,
    pub url: String,
    pub url_host: String,
    pub url_type: String,
    pub url__is_google_map: bool,
    pub url__is_eventbrite_event: bool,
    pub url__google_calendar: bool,
    pub url__is_social: bool,
    pub url__contains_event: bool
}

impl ElemDescription for UrlDesc {
    fn compare(&self, other: &Self, context: &Context) -> f32 {
        return url::url_similarity(self, other, context);
    }
}

impl UrlDesc {
    pub fn create_from_dict(py: &Python, di: &HashMap<String,PyObject>) -> UrlDesc {
        let d = UrlDesc {
            node_id: di["node_id"].extract::<String>(*py).unwrap(),
            url: di["url"].extract::<String>(*py).unwrap(),
            url_host: di["url_host"].extract::<String>(*py).unwrap(),
            url_type: di["url_type"].extract::<String>(*py).unwrap(),

            url__is_google_map: di["url__is_google_map"].extract::<bool>(*py).unwrap(),
            url__is_eventbrite_event: di["url__is_eventbrite_event"].extract::<bool>(*py).unwrap(),
            url__google_calendar: di["url__google_calendar"].extract::<bool>(*py).unwrap(),
            url__is_social: di["url__is_social"].extract::<bool>(*py).unwrap(),
            url__contains_event: di["url__contains_event"].extract::<bool>(*py).unwrap(),
        };
        return d;
    }
}


#[pyclass]
pub struct ComputedStylesDesc {
    pub all_computed_styles__array_int: Vec<i32>
}
impl ElemDescription for ComputedStylesDesc {
    fn compare(&self, other: &Self, context: &Context) -> f32 {
        return computed_styles::compare_computed_styles(self, other, context);
    }
}


#[pyclass]
pub struct FeatureSetDesc {
    pub feature_set_int: HashSet<i32>
}
impl ElemDescription for FeatureSetDesc {
    fn compare(&self, other: &Self, context: &Context) -> f32 {
        return feature_set::featureset_overlap(self, other, context);
    }
}


#[pyclass]
pub struct RectDesc {
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
    pub area: f32,
}

impl ElemDescription for RectDesc {
    // doesn't really have this trait but we must add it for creating Box<ElemDescription>
    fn compare(&self, other: &Self, context: &Context) -> f32 {
        panic!("RectDesc.compare() should never be called");
        return 0.0;
    }
}

#[pyclass]
#[derive(Clone)]
pub struct ContentDesc {

    pub node_id: String, //&'a str,
    pub tag_name: String, //&'a str,
    pub text: String, //&'a str,
    pub textL: String, //&'a str,
    pub num_tags: u16,

    pub start_tag: String,
    pub parent_tag_name: String,
    pub parent_start_tag: String,
    pub outer_html_no_content: String,
    pub outer_html_no_content_rev: String,
    pub parent_outer_html_no_content: String,

    pub text_is_more_link: bool,
    pub text_is_digit: bool,
    pub text_has_date: String,  // todo: this is sometimes None, use Option<&'a str> ?

    pub img_type: String,
    pub parent_img_type: String,

    //pub outer_html_no_content_for_sim: String,
    //pub outer_html_no_content_rev_for_sim: String,
    //pub parent_outer_for_sim: String,

    pub outer_html_no_content_for_sim: CString, //Option<*const c_char>,
    pub outer_html_no_content_rev_for_sim: CString, // Option<*const c_char>,
    pub parent_outer_for_sim: CString  //Option<*const c_char>,
}
impl ElemDescription for ContentDesc {
    // fn compare(&self, &other: &(dyn EuclideanDesc + 'static)) -> f32 {
    fn compare(&self, other: &Self, context: &Context) -> f32 {
        return content::compare_content(self, other, context);
    }
}


impl ContentDesc {
    pub fn create_from_dict(py: &Python, di: &HashMap<String,PyObject>, context: &Context) -> ContentDesc {

        let parent_outer_no_content = di["parent_outer_html_no_content"].extract::<String>(*py).unwrap();
        let outer_no_content = di["outer_html_no_content"].extract::<String>(*py).unwrap();

        // trunc_len drastically affects performance of compare_outer_sim()
        let mut trunc_len = parent_outer_no_content.len().min(430);
        if context.quick {
            trunc_len = parent_outer_no_content.len().min(300);
        }

        let outer_html_no_content_for_sim = CString::new(
            outer_no_content.to_ascii_lowercase()
        ).expect("CString::new failed");

        let parent_outer_for_sim = CString::new(
            parent_outer_no_content[..trunc_len].to_ascii_lowercase()
        ).expect("CString::new failed");

        let outer_no_content_rev = di["outer_html_no_content_rev"].extract::<String>(*py).unwrap();

        let outer_html_no_content_rev_for_sim = CString::new(
            outer_no_content_rev.clone()
        ).expect("CString::new failed");

        let desc_struct = ContentDesc {
            node_id: di["node_id"].extract::<String>(*py).unwrap(),
            tag_name: di["tag_name"].extract::<String>(*py).unwrap(),
            text: di["text"].extract::<String>(*py).unwrap(),
            textL: di["textL"].extract::<String>(*py).unwrap(),
            num_tags: di["num_tags"].extract::<u16>(*py).unwrap(),

            start_tag: di["start_tag"].extract::<String>(*py).unwrap(),
            parent_tag_name: di["parent_tag_name"].extract::<String>(*py).unwrap(),
            parent_start_tag: di["parent_start_tag"].extract::<String>(*py).unwrap(),
            outer_html_no_content: outer_no_content,
            outer_html_no_content_rev: di["outer_html_no_content_rev"].extract::<String>(*py).unwrap(),
            parent_outer_html_no_content: parent_outer_no_content,

            text_is_more_link: di["text_is_more_link"].extract::<bool>(*py).unwrap(),
            text_is_digit: di["text_is_digit"].extract::<bool>(*py).unwrap(),
            text_has_date: di["text_has_date"].extract::<String>(*py).unwrap(),

            img_type: di["img_type"].extract::<String>(*py).unwrap(),
            parent_img_type: di["parent_img_type"].extract::<String>(*py).unwrap(),

            outer_html_no_content_for_sim: outer_html_no_content_for_sim,
            outer_html_no_content_rev_for_sim: outer_html_no_content_rev_for_sim,
            parent_outer_for_sim: parent_outer_for_sim,
        };
        return desc_struct;
    }
}

/*
        let outer_html_no_content_for_sim = CString::new(
            ed.outer_html_no_content.to_ascii_lowercase()
        ).expect("CString::new failed");

        ed.outer_html_no_content_for_sim = Some(outer_html_no_content_for_sim.as_ptr());

        // trunc_len drastically affects performance of compare_outer_sim()
        let mut trunc_len = ed.parent_outer_html_no_content.len().min(430);
        if obj.context.quick {
            trunc_len = ed.parent_outer_html_no_content.len().min(300);
        }

        let parent_outer_for_sim = CString::new(
            ed.parent_outer_html_no_content[..trunc_len].to_ascii_lowercase()
        ).expect("CString::new failed");

        ed.parent_outer_for_sim = Some(parent_outer_for_sim.as_ptr());

        //let outer_html_no_content_rev: &String = &ed.outer_html_no_content_rev
        let outer_html_no_content_rev_for_sim = CString::new(
            ed.outer_html_no_content_rev.clone()
        ).expect("CString::new failed");

        ed.outer_html_no_content_rev_for_sim = Some(outer_html_no_content_rev_for_sim.as_ptr());
 */


pub struct VisibilityDesc {
    pub visibility__ALL_VISIBLE: bool,
    pub cssComputed__visibility: String,
    pub jquery__is_hidden: bool,
    pub cssComputed__display: String,
    pub driver__is_displayed: bool,
    pub spatial_visibility: String
}

impl ElemDescription for VisibilityDesc {
    fn compare(&self, other: &Self, context: &Context) -> f32 {
        return visibility::compare_visibility(self, other, context);
    }
}

impl VisibilityDesc {
    pub fn create_from_dict(py: &Python, di: &HashMap<String,PyObject>) -> VisibilityDesc {
        let d = VisibilityDesc {
            visibility__ALL_VISIBLE: di["visibility__ALL_VISIBLE"].extract::<bool>(*py).unwrap(),
            cssComputed__visibility: di["cssComputed__visibility"].extract::<String>(*py).unwrap(),
            jquery__is_hidden: di["jquery__is_hidden"].extract::<bool>(*py).unwrap(),
            cssComputed__display: di["cssComputed__display"].extract::<String>(*py).unwrap(),
            driver__is_displayed: di["driver__is_displayed"].extract::<bool>(*py).unwrap(),
            spatial_visibility: di["spatial_visibility"].extract::<String>(*py).unwrap(),
        };
        return d;
    }
}
