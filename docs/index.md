# pyevtgen

Python bindings for [EvtGen](https://gitlab.cern.ch/evtgen/evtgen), the Monte Carlo generator for particle decays, in particular weak decays of heavy-flavor hadrons.

The wheels are self-contained: EvtGen, HepMC3 and Pythia8 are compiled statically into the extension module, and the package ships EvtGen's default decay table, its particle table, and the Pythia8 data that the `PYTHIA` decay model needs. No ROOT installation or environment variables are required.

:::{note}
This is an unofficial package that is not maintained by the EvtGen authors.
:::

The pages below are Jupyter notebooks. They are executed whenever the documentation is built, so their output always reflects the current version of the package.

```{toctree}
---
maxdepth: 2
---
install
usage/basics
usage/decay-tree
usage/decay-files
usage/particle-properties
usage/fsr
usage/phase-space
usage/four-body
api
```
