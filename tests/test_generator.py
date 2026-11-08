# cspell:ignore allclose dalitz enddecay jpsi libstdc mumu usefixtures
from __future__ import annotations

import subprocess
import sys
from contextlib import nullcontext as does_not_raise
from textwrap import dedent
from typing import TYPE_CHECKING

import numpy as np
import pytest

import pyevtgen
from pyevtgen import Generator, final_state_momenta, phase_space

if TYPE_CHECKING:
    from pathlib import Path

requires_processes = pytest.mark.skipif(
    sys.platform == "emscripten", reason="Pyodide cannot start processes"
)

STABLE_PARTICLES = {
    "K+", "K-", "K_L0", "anti-n0", "anti-nu_e", "anti-nu_mu", "anti-nu_tau",
    "anti-p-", "e+", "e-", "gamma", "mu+", "mu-", "n0", "nu_e", "nu_mu",
    "nu_tau", "p+", "pi+", "pi-",
}  # fmt: skip


@requires_processes
def test_import_after_numpy():
    # NumPy loads the system libstdc++, which may be older than the build compiler's
    output = run_in_subprocess("""
        import numpy
        import pyevtgen
        print(pyevtgen.EVTGEN_VERSION)
    """)
    assert pyevtgen.EVTGEN_VERSION in output


def test_bundled_data_files():
    assert pyevtgen.DECAY_FILE.is_file()
    assert pyevtgen.PARTICLE_TABLE.is_file()
    assert (pyevtgen.PYTHIA8_XML_DIR / "Welcome.xml").is_file()


def test_versions():
    assert pyevtgen.EVTGEN_VERSION.startswith("R03-")
    assert pyevtgen.HEPMC3_VERSION.startswith("3.")
    assert pyevtgen.PYTHIA8_VERSION.startswith("83")


@pytest.mark.usefixtures("generator")
def test_single_instance():
    with pytest.raises(RuntimeError, match="only be initialized once"):
        Generator()


def test_missing_file():
    with pytest.raises(FileNotFoundError, match="does-not-exist"):
        Generator("does-not-exist.dec")


@pytest.mark.parametrize(
    ("particle", "expectation"),
    [
        ("D0", does_not_raise()),
        (421, does_not_raise()),
        ("not-a-particle", pytest.raises(KeyError, match="not-a-particle")),
        (999999999, pytest.raises(KeyError, match="999999999")),
    ],
)
def test_properties(generator: Generator, particle: str | int, expectation):
    with expectation:
        properties = generator.properties(particle)
        assert properties.name == "D0"
        assert properties.pdg_id == 421
        assert properties.mass == pytest.approx(1.86483)
        assert properties.charge == 0
        assert properties.spin2 == 0


def test_particles(generator: Generator):
    particles = generator.particles()
    assert len(particles) > 500
    names = {p.name for p in particles}
    assert {"B0", "D0", "J/psi", "pi+"} <= names


@pytest.mark.parametrize("parent", ["B0", "B+", "J/psi", "Upsilon(4S)", "Lambda_b0"])
def test_generate_decays_to_stable_particles(generator: Generator, parent: str):
    events = generator.generate(parent, n=200)
    assert len(events) == 200
    for event in events:
        assert event.name == parent
        assert event.decay_mode >= 0
        final_state = event.final_state()
        assert {p.name for p in final_state} <= STABLE_PARTICLES
        assert all(p.decay_mode == -1 for p in final_state)


def test_generate_conserves_four_momentum(generator: Generator):
    p4 = (10.0, 1.0, 2.0, 8.0)
    for event in generator.generate("D0", n=100, p4=p4):
        np.testing.assert_allclose(event.p4, p4)
        total = np.sum([p.p4 for p in event.final_state()], axis=0)
        np.testing.assert_allclose(total, p4, atol=1e-9)


def test_generate_at_rest(generator: Generator):
    event = generator.decay("D0")
    assert event.p4 == pytest.approx([1.86483, 0, 0, 0])
    assert event.mass == pytest.approx(1.86483)


def test_generate_is_reproducible(generator: Generator):
    def final_state_names(seed: int) -> list[list[str]]:
        generator.seed = seed
        assert generator.seed == seed
        events = generator.generate("B0", n=20)
        return [[p.name for p in event.final_state()] for event in events]

    assert final_state_names(7) == final_state_names(7)
    assert final_state_names(7) != final_state_names(8)


def test_generate_invalid_input(generator: Generator):
    with pytest.raises(ValueError, match="non-negative"):
        generator.generate("D0", n=-1)
    with pytest.raises(ValueError, match="four components"):
        generator.decay("D0", p4=(1.0, 0.0))
    assert generator.generate("D0", n=0) == []


def test_final_state_momenta_empty():
    assert final_state_momenta([]).shape == (0, 0, 4)


def run_in_subprocess(code: str) -> str:
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, "-c", dedent(code)],
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout.splitlines()[-1]


@pytest.fixture
def jpsi_to_mumu(tmp_path: Path) -> Path:
    path = tmp_path / "jpsi.dec"
    path.write_text(
        dedent("""
        Decay J/psi
        1.0 mu+ mu- FSR VLL;
        Enddecay
        End
        """)
    )
    return path


@requires_processes
def test_user_decay_file(jpsi_to_mumu: Path):
    output = run_in_subprocess(f"""
        from pyevtgen import Generator, final_state_momenta
        generator = Generator(user_decay_file={str(jpsi_to_mumu)!r}, seed=1)
        events = generator.generate("J/psi", n=100)
        print(final_state_momenta(events).shape)
    """)
    assert output == "(100, 2, 4)"


@requires_processes
def test_fsr(jpsi_to_mumu: Path):
    output = run_in_subprocess(f"""
        from pyevtgen import Generator
        generator = Generator(user_decay_file={str(jpsi_to_mumu)!r}, fsr=True, seed=1)
        events = generator.generate("J/psi", n=1000)
        print(sum(len(e.final_state()) > 2 for e in events))
    """)
    assert int(output) > 100


def _invariant_mass_squared(momenta: np.ndarray) -> np.ndarray:
    return momenta[..., 0] ** 2 - np.sum(momenta[..., 1:] ** 2, axis=-1)


@pytest.mark.parametrize(
    ("parent_mass", "masses"),
    [
        (1.8, [0.5, 0.14]),
        (3.097, [0.0, 0.135, 0.14]),
        (5.0, [1.0, 0.5, 0.25, 0.1]),
        (20.0, [0.5 + i / 10 for i in range(8)]),
    ],
)
def test_phase_space_kinematics(parent_mass: float, masses: list[float]):
    momenta = phase_space(parent_mass, masses, n=200, seed=0)
    assert momenta.shape == (200, len(masses), 4)
    expected_total = np.broadcast_to([parent_mass, 0, 0, 0], (200, 4))
    assert np.allclose(momenta.sum(axis=1), expected_total)
    expected_masses = np.broadcast_to(np.square(masses), (200, len(masses)))
    assert np.allclose(_invariant_mass_squared(momenta), expected_masses, atol=1e-8)


def test_phase_space_is_reproducible():
    first = phase_space(3.0, [0.1, 0.2, 0.3], n=10, seed=1)
    assert np.array_equal(first, phase_space(3.0, [0.1, 0.2, 0.3], n=10, seed=1))
    assert not np.array_equal(first, phase_space(3.0, [0.1, 0.2, 0.3], n=10, seed=2))


def _inside_dalitz_plot(
    s12: np.ndarray, s23: np.ndarray, parent_mass: float, masses: list[float]
) -> np.ndarray:
    m1, m2, m3 = masses
    e2 = (s12 - m1**2 + m2**2) / (2 * np.sqrt(s12))
    e3 = (parent_mass**2 - s12 - m3**2) / (2 * np.sqrt(s12))
    p2 = np.sqrt(np.maximum(e2**2 - m2**2, 0))
    p3 = np.sqrt(np.maximum(e3**2 - m3**2, 0))
    lower = (e2 + e3) ** 2 - (p2 + p3) ** 2
    upper = (e2 + e3) ** 2 - (p2 - p3) ** 2
    return (lower <= s23) & (s23 <= upper)


def _flat_dalitz_histogram(
    parent_mass: float, masses: list[float], bin_ranges: list[tuple[float, float]]
) -> np.ndarray:
    rng = np.random.default_rng(seed=0)
    s12 = rng.uniform(*bin_ranges[0], size=4_000_000)
    s23 = rng.uniform(*bin_ranges[1], size=4_000_000)
    inside = _inside_dalitz_plot(s12, s23, parent_mass, masses)
    histogram, _, _ = np.histogram2d(
        s12[inside], s23[inside], bins=10, range=bin_ranges
    )
    return histogram


@pytest.mark.parametrize(
    ("parent_mass", "masses"),
    [
        (3.0, [0.1, 0.2, 0.3]),
        (5.28, [1.87, 0.49, 0.14]),
    ],
)
def test_phase_space_is_uniform_in_dalitz_plot(parent_mass: float, masses: list[float]):
    n_events = 500_000
    momenta = phase_space(parent_mass, masses, n=n_events, seed=0)
    s12 = _invariant_mass_squared(momenta[:, 0] + momenta[:, 1])
    s23 = _invariant_mass_squared(momenta[:, 1] + momenta[:, 2])
    s12_range = (masses[0] + masses[1]) ** 2, (parent_mass - masses[2]) ** 2
    s23_range = (masses[1] + masses[2]) ** 2, (parent_mass - masses[0]) ** 2
    bin_ranges = [s12_range, s23_range]
    observed, _, _ = np.histogram2d(s12, s23, bins=10, range=bin_ranges)

    reference = _flat_dalitz_histogram(parent_mass, masses, bin_ranges)
    scale = n_events / reference.sum()
    expected = scale * reference
    mask = expected > 50
    variance = expected + scale**2 * reference
    chi2 = np.sum((observed - expected)[mask] ** 2 / variance[mask])
    assert chi2 / (np.count_nonzero(mask) - 1) < 1.5


def test_phase_space_next_to_generator(generator: Generator):
    phase_space(3.0, [0.1, 0.2, 0.3], n=1, seed=0)
    assert generator.decay("D0").name == "D0"


@pytest.mark.parametrize(
    ("parent_mass", "masses", "n", "match"),
    [
        (1.0, [0.6, 0.6], 1, "must exceed"),
        (1.0, [0.5, 0.5], 1, "must exceed"),
        (1.0, [0.1], 1, "2 to 15"),
        (9.0, [0.1] * 16, 1, "2 to 15"),
        (1.0, [-0.1, 0.1], 1, "non-negative"),
        (1.0, [float("nan"), 0.1], 1, "non-negative"),
        (1.0, [0.1, 0.1], -1, "non-negative"),
    ],
)
def test_phase_space_invalid_input(
    parent_mass: float, masses: list[float], n: int, match: str
):
    with pytest.raises(ValueError, match=match):
        phase_space(parent_mass, masses, n=n)


def test_phase_space_without_events():
    assert phase_space(3.0, [0.1, 0.2], n=0).shape == (0, 2, 4)
