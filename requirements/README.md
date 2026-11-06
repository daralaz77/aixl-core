# Hash-pinned requirements

`*.in` are the human-edited inputs; `*.txt` are generated with `pip-compile --generate-hashes --allow-unsafe --strip-extras` on Python 3.11 (the oldest supported) and installed with `pip install --require-hashes -r requirements/<name>.txt`, so a tampered or substituted package fails the install (OpenSSF Scorecard: pinned dependencies).

| file | used by |
|---|---|
| `ci.txt` | the `tests` workflow (pytest matrix) and the `docker-publish` smoke test |
| `docker.txt` | the `Dockerfile` (the A2A agent image) |
| `lint.txt` | the `lint` job (ruff) |
| `build.txt` | the `wheel` job |

Regenerate after editing an `.in` file: `pip install pip-tools`, then from this folder `pip-compile --generate-hashes --allow-unsafe --strip-extras --output-file=ci.txt ci.in` (same for the others). Dependabot (`pip` ecosystem) opens pull requests for these files.
