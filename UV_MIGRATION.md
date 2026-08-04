# Dependency management: pip -> uv

## Before

- Tooling: pip + `requirements.txt` (loose `>=` version floors, no lockfile)
- Install command: `pip install -r requirements.txt`
- Measured cold install (fresh venv, `--no-cache-dir`, macOS arm64, Python 3.11.9):
  - Time: 41.9s wall clock
  - Packages installed: 168

## After

- Tooling: uv + `pyproject.toml` + `uv.lock` (fully locked, reproducible resolution)
- Install command: `uv sync`
- Measured install (fresh `.venv`, uv's local package cache warm from the migration step):
  - Time: 0.94s wall clock
  - Packages installed: 166 (175 resolved total in the lock; a few are conditional/platform markers)
- `requires-python` set to `>=3.11,<3.13` (repo had no explicit Python pin; the upper bound was
  added because `llvmlite`/`numba`, pulled in transitively by `shap`, do not have working builds
  above 3.12 yet). `[tool.uv].constraint-dependencies` pins `llvmlite>=0.44` and `numba>=0.60` to
  stop the resolver from selecting an ancient `llvmlite` release that can't build on Python 3.11+.
- `requirements.txt` deleted; `pyproject.toml` + `uv.lock` are now the single source of truth.

## Verification

- `uv run python -c "import streamlit; import pandas; import geopandas; import shap; import gradio; import plotly; import pydeck"` succeeded.
- `python -m py_compile` on both `app/streamlit_app.py` and `app/app_gradio.py` succeeded.
- No `tests/` directory exists in this repo, so no test suite was run.

## Takeaway

The 0.94s uv number is not an apples-to-apples cold-cache comparison, it reflects uv's local
package cache from the preceding `uv add`/`uv lock` steps, which is itself part of uv's normal
workflow and value proposition versus pip's always-cold installs. Even accounting for that, the
bigger win is reproducibility: pip had no lockfile and resolved floors non-deterministically,
while `uv.lock` pins exact versions and hashes for every install going forward.
