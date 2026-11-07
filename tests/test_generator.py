# cspell:ignore allclose enddecay jpsi mumu usefixtures
from __future__ import annotations

import subprocess
import sys
from contextlib import nullcontext as does_not_raise
from textwrap import dedent
from typing import TYPE_CHECKING

import numpy as np
import pytest

import pyevtgen
from pyevtgen import Generator, final_state_momenta

if TYPE_CHECKING:
    from pathlib import Path

STABLE_PARTICLES = {
    "K+", "K-", "K_L0", "anti-n0", "anti-nu_e", "anti-nu_mu", "anti-nu_tau",
    "anti-p-", "e+", "e-", "gamma", "mu+", "mu-", "n0", "nu_e", "nu_mu",
    "nu_tau", "p+", "pi+", "pi-",
}  # fmt: skip


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


def test_user_decay_file(jpsi_to_mumu: Path):
    output = run_in_subprocess(f"""
        from pyevtgen import Generator, final_state_momenta
        generator = Generator(user_decay_file={str(jpsi_to_mumu)!r}, seed=1)
        events = generator.generate("J/psi", n=100)
        print(final_state_momenta(events).shape)
    """)
    assert output == "(100, 2, 4)"


def test_fsr(jpsi_to_mumu: Path):
    output = run_in_subprocess(f"""
        from pyevtgen import Generator
        generator = Generator(user_decay_file={str(jpsi_to_mumu)!r}, fsr=True, seed=1)
        events = generator.generate("J/psi", n=1000)
        print(sum(len(e.final_state()) > 2 for e in events))
    """)
    assert int(output) > 100
