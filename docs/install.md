# Installation

## Package index

Development wheels are built from the default branch and published to a [package index](https://redeboer.github.io/pyevtgen-test/simple/pyevtgen/) that is hosted next to this documentation. Wheels are available for Linux (x86_64, aarch64) and macOS (arm64, x86_64) for Python 3.11 and newer. The index keeps the five latest versions.

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

## Build from source

Building from source requires network access, because CMake downloads the pinned EvtGen, HepMC3 and Pythia8 sources, and a C++17 compiler. [Pixi](https://pixi.sh) provides the compilers and build tools:

```shell
git clone https://github.com/redeboer/pyevtgen-test
cd pyevtgen-test
pixi run test
pixi run doc
```
