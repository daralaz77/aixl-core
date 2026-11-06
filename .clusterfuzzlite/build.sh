#!/bin/bash -eu
# The wheel builds and installs cleanly (the `wheel` CI job proves it), so the harnesses import the INSTALLED package, resources included.
pip3 install .
for fuzzer in $(find fuzz -name 'fuzz_*.py'); do
  compile_python_fuzzer "$fuzzer"
done
