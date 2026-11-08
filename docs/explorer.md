# Decay explorer

The decay explorer is an interactive [marimo](https://marimo.io) app that runs `pyevtgen` in your browser through [Pyodide](https://pyodide.org). Nothing has to be installed, and the controls update the plots immediately.

<p><a class="btn btn-primary" href="explorer/index.html" target="_blank">Open the decay explorer</a></p>

The app has two parts:

- **Phase space** for a parent mass and a final state of 2 to 7 particles that you choose, generated with {py:func}`.phase_space`. A parent momentum boosts the events into the lab frame. The app shows the Dalitz plot for three daughters or all two-particle invariant masses for more, together with the energy and angular distributions in the lab.
- **EvtGen decays** of a parent particle that you choose, with the full decay table. The app draws the decay tree of an event, lists the most frequent final states, and shows the momentum spectra and the decay length. An editable user decay file forces a decay channel, for instance to compare the `D_DALITZ` model with uniform phase space.

Starting EvtGen takes about 15 seconds in the browser. EvtGen stops the program on a malformed decay file, so reload the page if the app stops responding. The app is tested in a headless browser whenever the wheels are built.
