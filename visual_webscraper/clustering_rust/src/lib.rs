mod descs;
mod content;
mod computed_styles;
mod feature_set;
mod rect;
mod url;
mod visibility;

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use pyo3::types::PyBool;
use pyo3::types::PyUnicode;

use std::collections::HashSet;
use std::collections::HashMap;
use std::sync::mpsc;
use std::thread;

use descs::ElemDescription;
use crate::descs::ComputedStylesDesc;
use crate::descs::FeatureSetDesc;
use crate::descs::UrlDesc;
use crate::descs::Context;
use crate::descs::ContentDesc;


#[derive(PartialEq, Eq, Hash, Copy, Clone)]
struct ElemIndexPair {
    i: usize,
    j: usize
}

type SimsMap = HashMap<ElemIndexPair, f32>;
static NUM_CONTENT_THREADS: usize = 4;


/// for original working example see: /home/ross/code/events_project/py_rust_test/pyo3_test & string_sum_example

/// Formats the sum of two numbers as string.
/*
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}*/


/*
If you want to go from Python type -> Rust type then implementing FromPyObject is perfectly correct.
The other choice is to create a #[pyclass]. This allows you to use the same type in both languages.
So it depends if you need to share the same data to both languages, or want to just convert it all to Rust.
(going to use FromPyObject because conversion is sufficient)

impl FromPyObject<'_> for UrlDesc {
    fn extract(ob: &'_ PyAny) ->PyResult<Self> {
        unsafe {
            let py = Python::assume_gil_acquired();
            let obj = ob.to_object(py);
            Ok(UrlDesc {
                node_id: "1234".to_string(),
                url: "https://soas.ac.uk/".to_string()
            })
        }
    }
}

pub struct Context<'a> {
    pub page_url: &'a str,
    pub page_url_host: &'a str,
    pub page_height: f32,
    pub quick: bool
}
*/


fn get_num_sims(num_elems: usize) -> usize {
    ((num_elems * (&num_elems - 1)) / 2) as usize
}


#[pyfunction]
fn get_sims__content(py: Python, content_dicts: Vec<HashMap<String,PyObject>>, context: HashMap<String,PyObject>) -> PyResult<Vec<f32>> {

    let context_struct = descs::Context::create_from_dict(&py, context);

    let mut content_structs: Vec<descs::ContentDesc> = Vec::with_capacity(
        content_dicts.len()
    );
    let mut sims: Vec<f32> = Vec::with_capacity(
        get_num_sims(content_dicts.len())
    );

    for di in content_dicts.iter() {
        content_structs.push(
            descs::ContentDesc::create_from_dict(&py, di, &context_struct)
        );
    }

    for (i, struct1) in content_structs.iter().enumerate() {
        for (j, struct2) in content_structs.iter().enumerate() {
            if i >= j {
                continue;
            }
            sims.push(struct1.compare(struct2, &context_struct));
        }
    }

    return Ok(sims);
}


fn get_sims__content_thread(content_structs: Vec<descs::ContentDesc>, start: usize, end: usize, sender: mpsc::Sender<SimsMap>, context_struct: descs::Context) {
    let mut sims: SimsMap = HashMap::new();
    for (i, struct1) in content_structs.iter().enumerate() {

        if (i < start) || (i > end) {
            continue;
        }

        for (j, struct2) in content_structs.iter().enumerate() {
            if i >= j {
                continue;
            }
            let key = ElemIndexPair { i, j };
            sims.insert(key, struct1.compare(struct2, &context_struct));
        }

    }
    sender.send(sims).unwrap();
}



#[pyfunction]
fn get_sims__content_concurrent(py: Python, content_dicts: Vec<HashMap<String,PyObject>>, context: HashMap<String,PyObject>) -> PyResult<Vec<f32>> {

    let context_struct = descs::Context::create_from_dict(&py, context);

    let mut content_structs: Vec<descs::ContentDesc> = Vec::with_capacity(
        content_dicts.len()
    );
    for di in content_dicts.iter() {
        content_structs.push(
            descs::ContentDesc::create_from_dict(&py, di, &context_struct)
        );
    }
    let mut sims: Vec<f32> = Vec::with_capacity(
        get_num_sims(content_dicts.len())
    );

    let len = content_structs.len();

    let chunk_size = ((len as f32) / 4.0).round() as usize;
    let mut num_threads = 0;

    let (tx, rx): (std::sync::mpsc::Sender<SimsMap>, std::sync::mpsc::Receiver<SimsMap>) = mpsc::channel();

    for i in (0..len).step_by(chunk_size) {
        let start = i;
        let end = (&chunk_size) + i - 1;
        let sender = mpsc::Sender::clone(&tx);

        let ctx = context_struct.clone();
        let new_vec = content_structs.to_vec();

        num_threads = num_threads + 1;
        thread::spawn(move || {
            get_sims__content_thread(
                new_vec, start, end, sender, ctx
            );
      });
    }

    // collect results from threads
    let mut sims_collected: SimsMap = HashMap::new();
    for (i, received) in rx.iter().enumerate() {
      for (&key, &val) in received.iter() {
          sims_collected.insert(key, val);
      }
      if i == (num_threads-1) {
          break;
      }
    }

    for (i, struct1) in content_structs.iter().enumerate() {
        for (j, struct2) in content_structs.iter().enumerate() {
            if i >= j {
                continue;
            }
            let key = ElemIndexPair { i, j };
            if ! sims_collected.contains_key(&key) {
                panic!("key not found: {},{}", i, j);
            }
            sims.push(*(sims_collected.get(&key).unwrap()));
        }
    }

    return Ok(sims);
}


#[pyfunction]
fn get_sims__feature_set(py: Python, fs_dicts: Vec<HashMap<String,PyObject>>, context: HashMap<String,PyObject>) -> PyResult<Vec<f32>> {

    let context_struct = descs::Context::create_from_dict(&py, context);

    let mut fs_structs: Vec<descs::FeatureSetDesc> = Vec::with_capacity(
        fs_dicts.len()
    );
    let mut sims: Vec<f32> = Vec::with_capacity(
        get_num_sims(fs_dicts.len())
    );

    println!("num elems: {} num sims: {}", fs_dicts.len(), get_num_sims(fs_dicts.len()));

    for di in fs_dicts.iter() {
        fs_structs.push(
            descs::FeatureSetDesc {
                feature_set_int: di["feature_set_int"].extract::<HashSet<i32>>(py).unwrap()
            }
        );
    }

    for (i, struct1) in fs_structs.iter().enumerate() {
        for (j, struct2) in fs_structs.iter().enumerate() {
            if i >= j {
                continue;
            }
            sims.push(struct1.compare(struct2, &context_struct));
        }
    }

    return Ok(sims);
}


#[pyfunction]
fn get_sims__css(py: Python, css_dicts: Vec<HashMap<String,PyObject>>, context: HashMap<String,PyObject>) -> PyResult<Vec<f32>> {

    let context_struct = descs::Context::create_from_dict(&py, context);

    let mut css_structs: Vec<descs::ComputedStylesDesc> = Vec::with_capacity(css_dicts.len());
    let mut sims: Vec<f32> = Vec::with_capacity(
        get_num_sims(css_dicts.len())
    );

    for di in css_dicts.iter() {
        css_structs.push(
            descs::ComputedStylesDesc {
                all_computed_styles__array_int: di["all_computed_styles__array_int"].extract::<Vec<i32>>(py).unwrap()
            }
        );
    }

    for (i, struct1) in css_structs.iter().enumerate() {
        for (j, struct2) in css_structs.iter().enumerate() {
            if i >= j {
                continue;
            }
            sims.push(struct1.compare(struct2, &context_struct));
        }
    }

    return Ok(sims);
}

#[pyfunction]
fn get_sims__url(py: Python, url_dicts: Vec<HashMap<String,PyObject>>, context: HashMap<String,PyObject>) -> PyResult<Vec<f32>> {

    let context_struct = descs::Context::create_from_dict(&py, context);

    let mut url_structs: Vec<descs::UrlDesc> = Vec::with_capacity(url_dicts.len());
    let mut sims: Vec<f32> = Vec::with_capacity(
        get_num_sims(url_dicts.len())
    );

    for di in url_dicts.iter() {
        url_structs.push(
            descs::UrlDesc::create_from_dict(&py, di)
        );
    }

    for (i, struct1) in url_structs.iter().enumerate() {
        for (j, struct2) in url_structs.iter().enumerate() {
            if i >= j {
                continue;
            }
            sims.push(struct1.compare(struct2, &context_struct));
        }
    }

    return Ok(sims);
}


#[pyfunction]
fn get_sims__rect(py: Python, rect_dicts: Vec<HashMap<String,PyObject>>, context: HashMap<String,PyObject>) -> (Vec<f32>, Vec<f32>, Vec<f32>, Vec<f32>) {
    //let mut sims: Vec<f32> = Vec::new();

    let mut area_sims: Vec<f32> = Vec::new();
    let mut euclidean_sims: Vec<f32> = Vec::new();
    let mut spatially_aligned_sims: Vec<f32> = Vec::new();
    let mut area_alignment_sims: Vec<f32> = Vec::new();

    let context_struct = descs::Context::create_from_dict(&py, context);

    let mut rect_structs: Vec<descs::RectDesc> = Vec::with_capacity(rect_dicts.len());
    let mut sims: Vec<f32> = Vec::with_capacity(
        get_num_sims(rect_dicts.len())
    );

    for di in rect_dicts.iter() {
        // todo: create method for this
        let rect_struct = descs::RectDesc {
            x: di["x"].extract::<f32>(py).unwrap(),
            y: di["y"].extract::<f32>(py).unwrap(),
            width: di["width"].extract::<f32>(py).unwrap(),
            height: di["height"].extract::<f32>(py).unwrap(),
            area: di["area"].extract::<f32>(py).unwrap()
        };
        rect_structs.push(rect_struct);
    }

    for (i, desc1) in rect_structs.iter().enumerate() {
        for (j, desc2) in rect_structs.iter().enumerate() {
            if i >= j {
                continue;
            }
            area_sims.push(
                rect::area::areas_similar(&desc1, &desc2, &context_struct)
            );
            euclidean_sims.push(
                rect::euclidean::adjusted_euclidean_distance(desc1, &desc2, &context_struct)
            );
            spatially_aligned_sims.push(
                rect::spatially_aligned::spatially_aligned(desc1, &desc2, &context_struct)
            );
            area_alignment_sims.push(
                rect::area_alignment::area_alignment_simple(desc1, &desc2, &context_struct)
            )
        }
    }

    return (area_sims, euclidean_sims, spatially_aligned_sims, area_alignment_sims);
}


#[pyfunction]
fn get_sims__visibility(py: Python, visibility_dicts: Vec<HashMap<String,PyObject>>, context: HashMap<String,PyObject>) -> PyResult<Vec<f32>> {

    let context_struct = descs::Context::create_from_dict(&py, context);

    let mut visibility_structs: Vec<descs::VisibilityDesc> = Vec::with_capacity(visibility_dicts.len());
    let mut sims: Vec<f32> = Vec::with_capacity(
        get_num_sims(visibility_dicts.len())
    );

    for di in visibility_dicts.iter() {
        visibility_structs.push(
            descs::VisibilityDesc::create_from_dict(&py, di)
        );
    }

    for (i, struct1) in visibility_structs.iter().enumerate() {
        for (j, struct2) in visibility_structs.iter().enumerate() {
            if i >= j {
                continue;
            }
            sims.push(struct1.compare(struct2, &context_struct));
        }
    }

    return Ok(sims);
}


#[pymodule]
fn rust_descs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(get_sims__content))?;
    m.add_wrapped(wrap_pyfunction!(get_sims__content_concurrent))?;
    m.add_wrapped(wrap_pyfunction!(get_sims__css))?;
    m.add_wrapped(wrap_pyfunction!(get_sims__feature_set))?;
    m.add_wrapped(wrap_pyfunction!(get_sims__rect))?;
    m.add_wrapped(wrap_pyfunction!(get_sims__url))?;
    m.add_wrapped(wrap_pyfunction!(get_sims__visibility))?;
    Ok(())
}
