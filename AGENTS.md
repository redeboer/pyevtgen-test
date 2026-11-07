<!-- cspell:ignore conftest tombi -->

# Agent instructions

`src/bindings.cpp` wraps EvtGen with nanobind into `pyevtgen._core`; `src/pyevtgen/_generator.py` adds the public Python layer. `CMakeLists.txt` downloads pinned EvtGen, HepMC3 and Pythia8 sources and compiles them into static libraries instead of using their build systems, because EvtGen's CMake requires ROOT.

Use the Pixi tasks (`pixi task list`): `pixi run test` builds and tests, `pixi run style` runs the pre-commit hooks through prek, and `pixi run upgrade` upgrades lock files. Pixi only provides the compilers, CMake, Ninja and uv; uv manages the Python environment and rebuilds the extension when C++ or CMake files change (`[tool.uv] cache-keys`).

Developer configuration (`.vscode/`, `.envrc`, Ruff, ty and Tombi settings) is managed by the `check-dev-files` hook of [ComPWA/policy](https://github.com/ComPWA/policy), configured under `[tool.compwa.policy]` in `pyproject.toml`. Change those options rather than editing the generated files by hand. GitHub workflows are exempt (`no-github-actions`) and maintained by hand: tests run in `wheels.yml` against the built wheels, so `ci.yml` only runs the style checks.

EvtGen can be initialized only once per process. Tests share the session-scoped `generator` fixture from `conftest.py`, which is also injected into doctests; a test that needs a different configuration runs in a subprocess.
