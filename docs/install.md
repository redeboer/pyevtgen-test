# Installation

## Package index

Development wheels are built from the default branch and published to a [package index](https://redeboer.github.io/pyevtgen-test/simple/pyevtgen/) that is hosted next to this documentation. Wheels are available for Linux (x86_64, aarch64) and macOS (arm64, x86_64) for Python 3.11 and newer, and for [Pyodide](#pyodide). The index keeps the five latest versions.

```shell
uv pip install pyevtgen --index https://redeboer.github.io/pyevtgen-test/simple
```

To depend on these builds in a project, add the index to its `pyproject.toml`. Run `uv lock --upgrade-package pyevtgen` to pick up a new build:

```toml
[[tool.uv.index]]
explicit = true
name = "pyevtgen"
url = "https://redeboer.github.io/pyevtgen-test/simple"

[tool.uv.sources]
pyevtgen = { index = "pyevtgen" }
```

## Pyodide

The index also contains wheels for [Pyodide](https://pyodide.org), which runs Python in the browser through WebAssembly. Install them with [micropip](https://micropip.pyodide.org), for instance in [JupyterLite](https://jupyterlite.readthedocs.io) or the [Pyodide console](https://pyodide.org/en/stable/console.html):

```python
import micropip

await micropip.install(
    "pyevtgen", index_urls="https://redeboer.github.io/pyevtgen-test/simple"
)
```

Wheels are built for the Pyodide releases that use Python 3.13 and 3.14. Creating a {py:class}`.Generator` takes about 15 seconds there, about one and a half times as long as natively. Pyodide cannot start processes, so comparing settings that need a new {py:class}`.Generator`, as on the {doc}`usage/fsr` page, is not possible there.

## Build from source

Building from source requires network access, because CMake downloads the pinned EvtGen, HepMC3 and Pythia8 sources, and a C++17 compiler. [Pixi](https://pixi.sh) provides the compilers and build tools:

```shell
git clone https://github.com/redeboer/pyevtgen-test
cd pyevtgen-test
pixi run test
pixi run doc
```
