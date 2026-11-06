#!/bin/bash -eu
# aixl-core has no runtime dependency and is never pip-installed (same as CI and local dev, see .github/workflows/tests.yml): PyInstaller
# finds the package straight from the checkout through PYTHONPATH. It only bundles .py files, so the package data (aixl/resources: config.json,
# the arbiter rules) is added explicitly (found by the first run of this workflow: FileNotFoundError .../aixl/resources/config.json).
export PYTHONPATH="$PWD"
for fuzzer in $(find fuzz -name 'fuzz_*.py'); do
  compile_python_fuzzer "$fuzzer" --add-data "aixl/resources:aixl/resources"
done
