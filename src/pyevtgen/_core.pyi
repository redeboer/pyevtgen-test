"""Low-level bindings to the EvtGen C++ library."""

from collections.abc import Sequence
from typing import Annotated

import numpy
from numpy.typing import NDArray


EVTGEN_VERSION: str = 'R03-01-00'

HEPMC3_VERSION: str = '3.3.1'

PYTHIA8_VERSION: str = '8318'

class Particle:
    """
    A particle in a generated decay tree.

    Momenta are in GeV in the lab frame. Positions are in mm, with the time component as c*t.
    """

    @property
    def name(self) -> str:
        """EvtGen particle name."""

    @property
    def pdg_id(self) -> int:
        """PDG Monte Carlo particle ID."""

    @property
    def p4(self) -> list[float]:
        """Four-momentum (E, px, py, pz) in GeV."""

    @property
    def position(self) -> list[float]:
        """Production four-position (ct, x, y, z) in mm."""

    @property
    def lifetime(self) -> float:
        """Sampled proper decay time as c*t in mm."""

    @property
    def decay_mode(self) -> int:
        """
        Index of the decay channel in the decay table, or -1 if the particle did not decay.
        """

    @property
    def daughters(self) -> list[Particle]:
        """Direct decay products."""

    @property
    def mass(self) -> float:
        """Invariant mass of p4 in GeV."""

    def final_state(self) -> list[Particle]:
        """Return the stable particles at the leaves of the decay tree."""

    def __repr__(self) -> str: ...

class ParticleProperties:
    """Entry of the EvtGen particle table (evt.pdl)."""

    @property
    def name(self) -> str: ...

    @property
    def pdg_id(self) -> int: ...

    @property
    def mass(self) -> float:
        """Nominal mass in GeV."""

    @property
    def width(self) -> float:
        """Width in GeV."""

    @property
    def min_mass(self) -> float:
        """Lower mass cut-off in GeV."""

    @property
    def max_mass(self) -> float:
        """Upper mass cut-off in GeV."""

    @property
    def ctau(self) -> float:
        """Mean proper decay length in mm."""

    @property
    def charge(self) -> float:
        """Electric charge in units of e."""

    @property
    def spin2(self) -> int:
        """Twice the spin."""

    def __repr__(self) -> str: ...

def phase_space(parent_mass: float, masses: Sequence[float], n: int, seed: int) -> Annotated[NDArray[numpy.float64], dict(shape=(None, None, None), order='C')]:
    """Generate n unweighted phase space decays in the parent rest frame."""

class Generator:
    """Wrapper around the EvtGen decay generator."""

    def __init__(self, decay_files: Sequence[str], particle_table: str, pythia_xml_dir: str, fsr: bool, seed: int, mixing_type: int) -> None: ...

    def read_user_decay_file(self, path: str) -> None:
        """Read a user decay file that overrides entries of the main decay table."""

    @property
    def seed(self) -> int: ...

    def set_seed(self, seed: int) -> None: ...

    def generate(self, parent: int | str, n: int, p4: Sequence[float] | None = None) -> list[Particle]:
        """Generate n decays of the parent particle, by default at rest."""

    def properties(self, particle: int | str) -> ParticleProperties:
        """Look up a particle by EvtGen name or PDG ID."""

    def particles(self) -> list[ParticleProperties]:
        """Return all entries of the particle table."""
