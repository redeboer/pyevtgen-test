# Run in the browser

`pyevtgen` also runs in the browser through [Pyodide](https://pyodide.org), which compiles Python to WebAssembly. The notebooks below open in [JupyterLite](https://jupyterlite.readthedocs.io), a Jupyter environment that runs entirely in your browser, so nothing has to be installed. Edit the cells and rerun them to experiment.

:::{note}
Each notebook first installs `pyevtgen` from the [package index](install.md#pyodide), which takes a few seconds. Creating a {py:class}`.Generator` takes about 15 seconds in the browser, and a notebook can only create one, so restart the kernel to create another.
:::

## Generating decays

Decay trees, the most frequent final states of a $D^0$, and the momentum spectra of its decay products.

```{jupyterlite} examples/generating-decays.ipynb
:new_tab: True
:new_tab_button_text: Open in JupyterLite
```

## Phase space

Dalitz plots and invariant masses of uniform phase space for masses that you choose. This notebook needs no {py:class}`.Generator`, so it is ready instantly.

```{jupyterlite} examples/phase-space.ipynb
:new_tab: True
:new_tab_button_text: Open in JupyterLite
```

## Decay files

A user decay file that you can edit to compare the `D_DALITZ` model with uniform phase space.

```{jupyterlite} examples/decay-files.ipynb
:new_tab: True
:new_tab_button_text: Open in JupyterLite
```

The notebooks are tested in Pyodide whenever the wheels are built.
