# cspell:ignore jpsi
"""Tests for the bindings that mirror the EvtGen C++ API."""

from __future__ import annotations

import subprocess
import sys
from textwrap import dedent
from typing import TYPE_CHECKING

import numpy as np
import pytest

from pyevtgen import (
    DECAY_FILE,
    PARTICLE_TABLE,
    EvtDecayTable,
    EvtGen,
    EvtGenKine,
    EvtId,
    EvtParticleFactory,
    EvtPDL,
    EvtSpinDensity,
    EvtSpinType,
    EvtVector4R,
    boostTo,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pyevtgen import Generator


def test_evt_pdl_lookups(generator: Generator):
    assert generator.evtgen is not None
    d0 = EvtPDL.getId("D0")
    assert EvtPDL.name(d0) == "D0"
    assert EvtPDL.getStdHep(d0) == 421
    assert EvtPDL.evtIdFromStdHep(421) == d0
    assert EvtPDL.name(EvtPDL.chargeConj(d0)) == "anti-D0"
    assert EvtPDL.getMeanMass(d0) == pytest.approx(1.86483)
    assert EvtPDL.chg3(EvtPDL.getId("pi+")) == 3
    assert EvtPDL.getSpinType(EvtPDL.getId("J/psi")) == EvtSpinType.VECTOR
    assert EvtSpinType.getSpin2(EvtSpinType.DIRAC) == 1
    assert EvtPDL.getId("no-such-particle").getId() == -1
    assert len({d0, EvtId(d0.getId(), d0.getAlias())}) == 1


def test_reset_mass(generator: Generator):
    assert generator.evtgen is not None
    rho = EvtPDL.getId("rho0")
    nominal = EvtPDL.getMeanMass(rho)
    try:
        EvtPDL.reSetMass(rho, 0.9)
        assert EvtPDL.getMeanMass(rho) == pytest.approx(0.9)
    finally:
        EvtPDL.reSetMass(rho, nominal)


def test_evt_vector4r():
    p = EvtVector4R(10.0, 0.0, 0.0, 9.8)
    assert list(p) == [10.0, 0.0, 0.0, 9.8]
    assert p * p == pytest.approx(10.0**2 - 9.8**2)
    assert p.mass() == pytest.approx(np.sqrt(10.0**2 - 9.8**2))
    assert list(p + p) == [20.0, 0.0, 0.0, 19.6]
    assert list(2.0 * p) == list(p * 2.0)
    at_rest = EvtVector4R(p.mass(), 0.0, 0.0, 0.0)
    np.testing.assert_allclose(list(boostTo(at_rest, p)), list(p))


def test_generate_decay(generator: Generator):
    evt_id = EvtPDL.getId("D*+")
    p4 = EvtVector4R(EvtPDL.getMeanMass(evt_id), 0.0, 0.0, 0.0)
    parent = EvtParticleFactory.particleFactory(evt_id, p4)
    try:
        parent.setDiagonalSpinDensity()
        generator.evtgen.generateDecay(parent)
        assert parent.treeStr().startswith("D*+ ->")
        assert parent.getNDaug() == 2
        total = parent.getDaug(0).getP4Lab() + parent.getDaug(1).getP4Lab()
        np.testing.assert_allclose(list(total), list(p4), atol=1e-12)
    finally:
        parent.deleteTree()


def test_decay_table(generator: Generator):
    assert generator.evtgen is not None
    table = EvtDecayTable.getInstance()
    d0 = EvtPDL.getId("D0")
    n_modes = table.getNMode(d0.getAlias())
    assert n_modes > 100
    decays = [table.getDecay(d0.getAlias(), i) for i in range(n_modes)]
    assert sum(d.getBranchingFraction() for d in decays) == pytest.approx(1.0)
    assert all(d.getParentId() == d0 for d in decays)


def test_only_one_evtgen(generator: Generator):
    assert generator.evtgen is not None
    with pytest.raises(RuntimeError, match="only be initialized once"):
        EvtGen([str(DECAY_FILE)], str(PARTICLE_TABLE))


def test_phase_space_kine():
    weight, momenta = EvtGenKine.PhaseSpace([0.135, 0.14, 0.14], 3.097)
    assert weight == 1.0
    assert len(momenta) == 3
    total = momenta[0] + momenta[1] + momenta[2]
    np.testing.assert_allclose(list(total), [3.097, 0, 0, 0], atol=1e-12)


def test_spin_density():
    rho = EvtSpinDensity()
    rho.setDim(3)
    rho.set(0, 1, 0.5 + 0.25j)
    assert rho.getDim() == 3
    assert rho.get(0, 1) == 0.5 + 0.25j
    assert rho.get(1, 0) == 0


@pytest.fixture
def jpsi_to_mumu(tmp_path: Path) -> Path:
    path = tmp_path / "jpsi.dec"
    path.write_text(
        dedent("""
        Decay J/psi
        1.0 mu+ mu- VLL;
        Enddecay
        End
        """)
    )
    return path


@pytest.mark.skipif(
    sys.platform == "emscripten", reason="Pyodide cannot start processes"
)
def test_polarized_decay(jpsi_to_mumu: Path):
    code = f"""
        from pyevtgen import EvtParticleFactory, EvtPDL, EvtSpinDensity, EvtVector4R
        from pyevtgen import Generator
        generator = Generator(user_decay_file={str(jpsi_to_mumu)!r}, seed=1)
        jpsi = EvtPDL.getId("J/psi")
        p4 = EvtVector4R(EvtPDL.getMeanMass(jpsi), 0, 0, 0)
        for state in range(3):
            rho = EvtSpinDensity()
            rho.setDim(3)
            rho.set(state, state, 1.0)
            total = 0.0
            for _ in range(5000):
                parent = EvtParticleFactory.particleFactory(jpsi, p4)
                parent.setSpinDensityForwardHelicityBasis(rho)
                generator.evtgen.generateDecay(parent)
                muon = parent.getDaug(0).getP4Lab()
                total += (muon.get(3) / muon.d3mag()) ** 2
                parent.deleteTree()
            print(total / 5000)
    """
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, "-c", dedent(code)], capture_output=True, check=True, text=True
    )
    transverse_plus, longitudinal, transverse_minus = map(
        float, result.stdout.splitlines()[-3:]
    )
    # <cos^2> is 2/5 for (1 + cos^2) and 1/5 for sin^2
    assert transverse_plus == pytest.approx(0.4, abs=0.02)
    assert transverse_minus == pytest.approx(0.4, abs=0.02)
    assert longitudinal == pytest.approx(0.2, abs=0.02)
