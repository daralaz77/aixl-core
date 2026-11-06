#!/bin/bash -eu
# The wheel builds and installs cleanly (the `wheel` CI job proves it), so the harnesses import the INSTALLED package.
# PyInstaller only bundles .py files: the package's data files (aixl/resources: config.json, the arbiter rules) are added explicitly,
# found by the first run of this very workflow (FileNotFoundError: .../aixl/resources/config.json inside the bundled fuzzer).
pip3 install .
for fuzzer in $(find fuzz -name 'fuzz_*.py'); do
  compile_python_fuzzer "$fuzzer" --add-data "aixl/resources:aixl/resources"
done
