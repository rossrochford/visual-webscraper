use std::process::Command;
use std::env;
use std::path::Path;

fn main() {
    let out_dir = "/home/ross/code/events_project/webextractor/webextractor/clustering_rust/target/c_compiled";
    //let out_dir = "/home/ross/code/events_project/sim_matrix_worker_rust_text/target/c_compiled";
    //env::var("OUT_DIR").unwrap();

    // note that there are a number of downsides to this approach, the comments
    // below detail how to improve the portability of these commands.
    Command::new("gcc").args(&["src/simil.c", "-c", "-fPIC", "-o"])
                       .arg(&format!("{}/simil.o", out_dir))
                       .status().unwrap();
    Command::new("ar").args(&["crus", "libsimil.a", "simil.o"])
                      .current_dir(&Path::new(&out_dir))
                      .status().unwrap();

    println!("cargo:rustc-link-search=native={}", out_dir);
    println!("cargo:rustc-link-lib=static=simil");
}