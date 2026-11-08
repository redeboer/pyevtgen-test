import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="pyevtgen decay explorer")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Decay explorer

    This app runs [EvtGen](https://gitlab.cern.ch/evtgen/evtgen) in your browser through [`pyevtgen`](https://redeboer.github.io/pyevtgen-test) and [Pyodide](https://pyodide.org). The first part generates uniform phase space for masses that you choose, the second part decays particles with the full EvtGen decay table.
    """)


@app.cell(hide_code=True)
async def _():
    import sys

    if sys.platform == "emscripten":
        from urllib.parse import urljoin

        import js
        import micropip

        # Prefer the index that is hosted next to this app, so that a local build
        # of the documentation uses its own wheels
        _indices = [
            urljoin(str(js.location.href), "../simple"),
            "https://redeboer.github.io/pyevtgen-test/simple",
        ]
        for _index in _indices:
            try:
                await micropip.install("pyevtgen", index_urls=_index)
                break
            except ValueError:
                continue
    pyevtgen_installed = True
    return (pyevtgen_installed,)


@app.cell(hide_code=True)
def _(pyevtgen_installed):
    assert pyevtgen_installed
    import matplotlib.pyplot as plt
    import numpy as np

    import pyevtgen

    return np, plt, pyevtgen


@app.cell(hide_code=True)
def _(mo, pyevtgen):
    from importlib.metadata import version

    mo.md(
        f"Running pyevtgen {version('pyevtgen')} with EvtGen {pyevtgen.EVTGEN_VERSION}"
        f" and Pythia {pyevtgen.PYTHIA8_VERSION}."
    )


@app.cell(hide_code=True)
def _(np):
    PARTICLE_MASSES = {
        "gamma": 0.0,
        "e-": 0.000511,
        "mu-": 0.10566,
        "pi0": 0.13498,
        "pi+": 0.13957,
        "K+": 0.49368,
        "K0": 0.49761,
        "eta": 0.54786,
        "p+": 0.93827,
        "n0": 0.93957,
        "Lambda0": 1.11568,
        "D0": 1.86484,
    }

    def mass_squared(p: np.ndarray) -> np.ndarray:
        return p[..., 0] ** 2 - np.sum(p[..., 1:] ** 2, axis=-1)

    def boost_z(momenta: np.ndarray, parent_mass: float, momentum: float) -> np.ndarray:
        """Boost four-momenta from the parent rest frame along the z axis."""
        energy = np.hypot(parent_mass, momentum)
        gamma, beta_gamma = energy / parent_mass, momentum / parent_mass
        boosted = momenta.copy()
        boosted[..., 0] = gamma * momenta[..., 0] + beta_gamma * momenta[..., 3]
        boosted[..., 3] = beta_gamma * momenta[..., 0] + gamma * momenta[..., 3]
        return boosted

    return PARTICLE_MASSES, boost_z, mass_squared


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Phase space

    Choose a parent mass and the particles in the final state. Phase space is generated instantly with `pyevtgen.phase_space()`, which does not need a decay table. With a parent momentum, the events are boosted along the $z$ axis into the lab frame.
    """)


@app.cell(hide_code=True)
def _(mo):
    parent_mass = mo.ui.number(
        start=0.1, stop=20.0, step=0.001, value=3.0969, label="Parent mass [GeV]"
    )
    parent_momentum = mo.ui.slider(
        start=0.0,
        stop=20.0,
        step=0.5,
        value=0.0,
        label="Parent momentum [GeV]",
        show_value=True,
    )
    n_daughters = mo.ui.slider(
        start=2, stop=7, step=1, value=3, label="Number of daughters", show_value=True
    )
    n_events = mo.ui.slider(
        start=1_000,
        stop=100_000,
        step=1_000,
        value=50_000,
        label="Events",
        show_value=True,
    )
    mo.vstack([
        mo.hstack([parent_mass, parent_momentum]),
        mo.hstack([n_daughters, n_events]),
    ])
    return n_daughters, n_events, parent_mass, parent_momentum


@app.cell(hide_code=True)
def _(PARTICLE_MASSES, mo, n_daughters):
    _defaults = ["pi+", "pi+", "K+", "pi0", "pi0", "gamma", "gamma"]
    daughters = mo.ui.array([
        mo.ui.dropdown(
            options=list(PARTICLE_MASSES), value=_defaults[i], label=f"Daughter {i}"
        )
        for i in range(n_daughters.value)
    ])
    mo.hstack(list(daughters), wrap=True, justify="start")
    return (daughters,)


@app.cell(hide_code=True)
def _(
    PARTICLE_MASSES,
    boost_z,
    daughters,
    mo,
    n_events,
    parent_mass,
    parent_momentum,
    pyevtgen,
):
    _masses = [PARTICLE_MASSES[name] for name in daughters.value]
    phsp_error = None
    phsp = None
    if sum(_masses) >= parent_mass.value:
        phsp_error = mo.callout(
            mo.md(
                f"The daughters ({sum(_masses):.4f} GeV) are heavier than the parent ({parent_mass.value} GeV)."
            ),
            kind="danger",
        )
    else:
        _rest = pyevtgen.phase_space(
            parent_mass.value, _masses, n=n_events.value, seed=0
        )
        phsp = boost_z(_rest, parent_mass.value, parent_momentum.value)
    phsp_labels = [f"{i}:{name}" for i, name in enumerate(daughters.value)]
    phsp_error
    return phsp, phsp_labels


@app.cell(hide_code=True)
def _(mass_squared, np, phsp, phsp_labels, plt):
    from itertools import combinations

    _fig = None
    if phsp is not None and phsp.shape[1] == 3:
        _fig, _ax = plt.subplots(figsize=(5, 4.5))
        _ax.hist2d(
            mass_squared(phsp[:, 0] + phsp[:, 1]),
            mass_squared(phsp[:, 1] + phsp[:, 2]),
            bins=70,
            cmin=1,
        )
        _ax.set_title("Dalitz plot")
        _ax.set_xlabel(f"$m^2$({phsp_labels[0]}, {phsp_labels[1]}) [GeV$^2$]")
        _ax.set_ylabel(f"$m^2$({phsp_labels[1]}, {phsp_labels[2]}) [GeV$^2$]")
    elif phsp is not None:
        _pairs = list(combinations(range(phsp.shape[1]), 2))
        _ncols = min(len(_pairs), 4)
        _nrows = -(-len(_pairs) // _ncols)
        _fig, _axes = plt.subplots(
            _nrows, _ncols, figsize=(3 * _ncols, 2.4 * _nrows), squeeze=False
        )
        for _ax, (_i, _j) in zip(_axes.flat, _pairs, strict=False):
            _ax.hist(
                np.sqrt(mass_squared(phsp[:, _i] + phsp[:, _j])),
                bins=50,
                histtype="stepfilled",
                alpha=0.7,
            )
            _ax.set_xlabel(f"m({phsp_labels[_i]}, {phsp_labels[_j]}) [GeV]", fontsize=8)
            _ax.set_yticks([])
        for _ax in list(_axes.flat)[len(_pairs) :]:
            _ax.axis("off")
        _fig.suptitle("Two-particle invariant masses")
    if _fig is not None:
        _fig.tight_layout()
    _fig


@app.cell(hide_code=True)
def _(np, phsp, phsp_labels, plt):
    _fig = None
    if phsp is not None:
        _fig, (_ax1, _ax2) = plt.subplots(ncols=2, figsize=(9, 3.2))
        for _i, _label in enumerate(phsp_labels):
            _p = phsp[:, _i]
            _ax1.hist(_p[:, 0], bins=60, histtype="step", label=_label)
            _cos = _p[:, 3] / np.maximum(np.linalg.norm(_p[:, 1:], axis=1), 1e-12)
            _ax2.hist(_cos, bins=40, range=(-1, 1), histtype="step", label=_label)
        _ax1.set_xlabel("energy in the lab [GeV]")
        _ax2.set_xlabel(r"$\cos\theta$ in the lab")
        _ax2.legend(fontsize=7)
        _fig.tight_layout()
    _fig


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## EvtGen decays

    The full decay table describes real decays, including intermediate resonances and their decay models. Starting EvtGen reads the decay table and initializes Pythia8, which takes about 15 seconds in the browser.
    """)


@app.cell(hide_code=True)
def _(mo):
    # Scripts cannot press buttons, so they run all cells, for instance in CI
    AS_SCRIPT = mo.app_meta().mode == "script"
    start = mo.ui.run_button(label="Start EvtGen")
    start
    return AS_SCRIPT, start


@app.cell(hide_code=True)
def _(AS_SCRIPT, mo, pyevtgen, start):
    mo.stop(
        not (start.value or AS_SCRIPT), mo.md("*Press the button to start EvtGen.*")
    )
    with mo.status.spinner(title="Initializing EvtGen..."):
        generator = pyevtgen.Generator(seed=1)
    mo.md("EvtGen is ready.")
    return (generator,)


@app.cell(hide_code=True)
def _(generator, mo):
    assert generator
    parent = mo.ui.dropdown(
        options=[
            "D0",
            "D+",
            "D_s+",
            "Lambda_c+",
            "B0",
            "B+",
            "B_s0",
            "J/psi",
            "tau-",
            "K_S0",
        ],
        value="D0",
        label="Parent",
    )
    lab_momentum = mo.ui.slider(
        start=0.0,
        stop=50.0,
        step=1.0,
        value=10.0,
        label="Parent momentum [GeV]",
        show_value=True,
    )
    n_decays = mo.ui.slider(
        start=500, stop=10_000, step=500, value=2_000, label="Decays", show_value=True
    )
    mo.hstack([parent, lab_momentum, n_decays])
    return lab_momentum, n_decays, parent


@app.cell(hide_code=True)
def _(generator, lab_momentum, n_decays, np, parent):
    parent_properties = generator.properties(parent.value)
    _energy = np.hypot(parent_properties.mass, lab_momentum.value)
    decays = generator.generate(
        parent.value, n=n_decays.value, p4=[_energy, 0.0, 0.0, lab_momentum.value]
    )
    return decays, parent_properties


@app.cell(hide_code=True)
def _(decays, mo):
    def _mermaid(particle, lines, counter):
        node = f"n{counter[0]}"
        counter[0] += 1
        label = particle.name.replace('"', "'")
        lines.append(f'  {node}["{label}"]')
        for daughter in particle.daughters:
            child = _mermaid(daughter, lines, counter)
            lines.append(f"  {node} --> {child}")
        return node

    _lines = ["graph LR"]
    _mermaid(decays[0], _lines, [0])
    mo.vstack([
        mo.md("**Decay tree of the first event**"),
        mo.mermaid("\n".join(_lines)),
    ])


@app.cell(hide_code=True)
def _(decays, mo):
    from collections import Counter

    _counts = Counter(" ".join(sorted(p.name for p in e.final_state())) for e in decays)
    mo.vstack([
        mo.md("**Most frequent final states**"),
        mo.ui.table(
            [
                {"final state": state, "fraction": f"{count / len(decays):.1%}"}
                for state, count in _counts.most_common(10)
            ],
            selection=None,
        ),
    ])


@app.cell(hide_code=True)
def _(decays, np, parent_properties, plt):
    _fig, (_ax1, _ax2) = plt.subplots(ncols=2, figsize=(9, 3.2))
    _spectra = {}
    for _event in decays:
        for _particle in _event.final_state():
            _spectra.setdefault(_particle.name, []).append(
                np.linalg.norm(_particle.p4[1:])
            )
    for _name in sorted(_spectra, key=lambda n: -len(_spectra[n]))[:5]:
        _ax1.hist(_spectra[_name], bins=50, histtype="step", label=_name)
    _ax1.set_xlabel("momentum in the lab [GeV]")
    _ax1.set_yscale("log")
    _ax1.legend(fontsize=7)
    if parent_properties.ctau > 0 and decays[0].daughters:
        _vertices = np.array([e.daughters[0].position for e in decays])
        _length = np.linalg.norm(_vertices[:, 1:], axis=1)
        _ax2.hist(_length, bins=50, histtype="stepfilled", alpha=0.7)
        _ax2.set_xlabel("decay length [mm]")
        _ax2.set_yscale("log")
        _ax2.set_title(rf"$c\tau$ = {parent_properties.ctau:.3g} mm", fontsize=9)
    else:
        _ax2.axis("off")
    _fig.tight_layout()
    _fig


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Force a decay channel

    A user decay file overrides entries of the decay table. Edit the file and apply it, for instance to compare the `D_DALITZ` model with uniform phase space (`PHSP`). EvtGen stops the program on a malformed decay file, so reload the page if the app stops responding.
    """)


@app.cell(hide_code=True)
def _(generator, mo):
    assert generator
    decay_file = mo.ui.code_editor(
        value="Decay D+\n1.0 K- pi+ pi+ D_DALITZ;\nEnddecay\nEnd\n",
        label="User decay file",
        min_height=120,
    )
    forced_parent = mo.ui.text(value="D+", label="Parent")
    apply = mo.ui.run_button(label="Apply and generate")
    mo.vstack([decay_file, mo.hstack([forced_parent, apply])])
    return apply, decay_file, forced_parent


@app.cell(hide_code=True)
def _(
    AS_SCRIPT,
    apply,
    decay_file,
    forced_parent,
    generator,
    mass_squared,
    mo,
    plt,
    pyevtgen,
):
    from pathlib import Path
    from tempfile import mkdtemp

    mo.stop(
        not (apply.value or AS_SCRIPT),
        mo.md("*Press the button to apply the decay file.*"),
    )
    _path = Path(mkdtemp()) / "user.dec"
    _path.write_text(decay_file.value)
    generator.read_user_decay_file(_path)
    _events = generator.generate(forced_parent.value, n=20_000)
    _states = {tuple(p.name for p in e.final_state()) for e in _events}
    if len(_states) == 1 and len(next(iter(_states))) == 3:
        _momenta = pyevtgen.final_state_momenta(_events)
        _names = next(iter(_states))
        _fig, _ax = plt.subplots(figsize=(5, 4.5))
        _ax.hist2d(
            mass_squared(_momenta[:, 0] + _momenta[:, 1]),
            mass_squared(_momenta[:, 0] + _momenta[:, 2]),
            bins=70,
            cmin=1,
        )
        _ax.set_xlabel(f"$m^2$({_names[0]}, {_names[1]}) [GeV$^2$]")
        _ax.set_ylabel(f"$m^2$({_names[0]}, {_names[2]}) [GeV$^2$]")
        _ax.set_title(f"{forced_parent.value} decays")
        _fig.tight_layout()
        _output = _fig
    else:
        _output = mo.md(
            f"The decay file gives {len(_states)} different final states. A Dalitz plot needs a single three-body final state."
        )
    _output


if __name__ == "__main__":
    app.run()
