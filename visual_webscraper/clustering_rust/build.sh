#!/bin/bash

cargo build --release

cp target/release/librust_descs.so ./rust_descs.so
