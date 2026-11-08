"""Python interface to the EvtGen generator and its bundled data files."""

# cspell:ignore allclose Mersenne

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from pyevtgen import _core
from pyevtgen._core import (
    EvtExternalGenList,
    EvtGen,
    EvtId,
    EvtMTRandomEngine,
    EvtParticle,
    EvtParticleFactory,
    EvtPDL,
    EvtRandom,
    EvtSpinType,
    EvtVector4R,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

DATA_DIR = Path(_core.__file__).parent / "data"
DECAY_FILE = DATA_DIR / "DECAY.DEC"
"""Default EvtGen decay table that is bundled with the package."""
PARTICLE_TABLE = DATA_DIR / "evt.pdl"
"""Default EvtGen particle table that is bundled with the package."""
PYTHIA8_XML_DIR = DATA_DIR / "pythia8" / "xmldoc"
"""Pythia8 settings and particle data, used by EvtGen's ``PYTHIA`` decay model."""


@dataclass(frozen=True)
class Particle:
    """Copy of a particle in a generated decay tree.

    Momenta are in GeV in the lab frame. Positions are in mm, with the time component
    as :math:`ct`. Unlike an :class:`.EvtParticle`, a copy stays valid after EvtGen
    deleted the tree it came from.
    """

    name: str
    """EvtGen particle name."""
    pdg_id: int
    """PDG Monte Carlo particle ID."""
    p4: tuple[float, float, float, float]
    """Four-momentum :math:`(E, p_x, p_y, p_z)` in GeV."""
    position: tuple[float, float, float, float]
    """Production four-position :math:`(ct, x, y, z)` in mm."""
    lifetime: float
    """Sampled proper decay time as :math:`c\\tau` in mm."""
    decay_mode: int
    """Index of the decay channel in the decay table, or -1 if the particle did not
    decay. Decays through the ``PYTHIA`` model report 0, because Pythia8 resets the
    selected channel."""
    daughters: tuple[Particle, ...]
    """Direct decay products."""

    @classmethod
    def from_evt_particle(cls, particle: EvtParticle) -> Particle:
        """Copy an EvtGen decay tree, see :meth:`.EvtParticle.getP4Lab`."""
        n_daughters = particle.getNDaug()
        return cls(
            name=particle.getName(),
            pdg_id=particle.getPDGId(),
            p4=tuple(particle.getP4Lab()),
            position=tuple(particle.get4Pos()),
            lifetime=particle.getLifetime(),
            decay_mode=particle.getChannel() if n_daughters else -1,
            daughters=tuple(
                cls.from_evt_particle(particle.getDaug(i)) for i in range(n_daughters)
            ),
        )

    @property
    def mass(self) -> float:
        """Invariant mass of :attr:`p4` in GeV."""
        energy, px, py, pz = self.p4
        return max(energy**2 - px**2 - py**2 - pz**2, 0.0) ** 0.5

    def final_state(self) -> list[Particle]:
        """Return the stable particles at the leaves of the decay tree."""
        if not self.daughters:
            return [self]
        return [p for daughter in self.daughters for p in daughter.final_state()]

    def __repr__(self) -> str:
        return (
            f"Particle(name={self.name!r}, pdg_id={self.pdg_id},"
            f" n_daughters={len(self.daughters)})"
        )


@dataclass(frozen=True)
class ParticleProperties:
    """Entry of the EvtGen particle table, see :class:`.EvtPDL`."""

    name: str
    pdg_id: int
    mass: float
    """Nominal mass in GeV."""
    width: float
    """Width in GeV."""
    min_mass: float
    """Lower mass cut-off in GeV."""
    max_mass: float
    """Upper mass cut-off in GeV."""
    ctau: float
    """Mean proper decay length in mm."""
    charge: float
    """Electric charge in units of :math:`e`."""
    spin2: int
    """Twice the spin."""

    @classmethod
    def from_evt_id(cls, evt_id: EvtId) -> ParticleProperties:
        return cls(
            name=EvtPDL.name(evt_id),
            pdg_id=EvtPDL.getStdHep(evt_id),
            mass=EvtPDL.getMeanMass(evt_id),
            width=EvtPDL.getWidth(evt_id),
            min_mass=EvtPDL.getMinMass(evt_id),
            max_mass=EvtPDL.getMaxMass(evt_id),
            ctau=EvtPDL.getctau(evt_id),
            charge=EvtPDL.chg3(evt_id) / 3,
            spin2=EvtSpinType.getSpin2(EvtPDL.getSpinType(evt_id)),
        )

    def __repr__(self) -> str:
        return (
            f"ParticleProperties(name={self.name!r}, pdg_id={self.pdg_id},"
            f" mass={self.mass:.6f})"
        )


class Generator:
    """EvtGen decay generator.

    This class sets up :class:`.EvtGen` with Pythia8 for the ``PYTHIA`` decay model,
    in the same way as EvtGen's C++ examples, and copies the generated decay trees
    into :class:`Particle` objects. The underlying :class:`.EvtGen` instance is
    available as :attr:`evtgen` for everything else that EvtGen offers.

    EvtGen keeps its particle and decay tables in global state, so only one
    generator can be created per process.

    Args:
        decay_file: Main decay table, or several tables that are read in order.
        particle_table: Particle property table in EvtGen's :file:`evt.pdl`
            format.
        user_decay_file: Decay file whose entries override those of the main
            decay table, for instance to force a single decay channel.
        fsr: Simulate final-state radiation with Vincia QED from Pythia8 for
            decay channels that are marked with ``FSR`` (or the deprecated
            ``PHOTOS``) in the decay table.
        seed: Seed for the Mersenne Twister random engine. A random seed is
            drawn if not given.
        mixing_type: Neutral meson mixing treatment, passed on to EvtGen's
            ``EvtCPUtil::setMixingType``.
    """

    def __init__(
        self,
        decay_file: str | os.PathLike | Sequence[str | os.PathLike] = DECAY_FILE,
        particle_table: str | os.PathLike = PARTICLE_TABLE,
        *,
        user_decay_file: str | os.PathLike | None = None,
        fsr: bool = False,
        seed: int | None = None,
        mixing_type: int = 1,
    ) -> None:
        if isinstance(decay_file, (str, os.PathLike)):
            decay_file = [decay_file]
        decay_files = [_existing_file(path) for path in decay_file]
        if seed is None:
            seed = secrets.randbits(32)
        self.random_engine = EvtMTRandomEngine(seed)
        """Random engine of EvtGen and Pythia8."""
        external = EvtExternalGenList(
            convertPythiaCodes=False,
            pythiaXmlDir=str(PYTHIA8_XML_DIR),
            photonType="gamma",
            useEvtGenRandom=True,
        )
        self.evtgen = EvtGen(
            decay_files,
            _existing_file(particle_table),
            self.random_engine,
            external.getVinciaQEDModel() if fsr else None,
            external.getListOfModels(),
            mixing_type,
        )
        """The underlying :class:`.EvtGen` instance."""
        if user_decay_file is not None:
            self.read_user_decay_file(user_decay_file)

    @property
    def seed(self) -> int:
        """Seed with which the random engine was last initialized."""
        return self.random_engine.lastSeed()

    @seed.setter
    def seed(self, value: int) -> None:
        self.random_engine.setSeed(value)

    def read_user_decay_file(self, path: str | os.PathLike) -> None:
        """Override entries of the decay table with those of a user decay file."""
        self.evtgen.readUDecay(_existing_file(path))

    def decay(
        self,
        parent: str | int,
        p4: Sequence[float] | None = None,
    ) -> Particle:
        """Generate a single decay tree.

        Args:
            parent: EvtGen particle name or PDG ID of the decaying particle.
            p4: Four-momentum :math:`(E, p_x, p_y, p_z)` of the parent in GeV.
                Defaults to the parent at rest with its nominal mass.
        """
        return self.generate(parent, n=1, p4=p4)[0]

    def generate(
        self,
        parent: str | int,
        n: int,
        p4: Sequence[float] | None = None,
    ) -> list[Particle]:
        """Generate :code:`n` decay trees, see :meth:`decay`."""
        if n < 0:
            msg = f"Number of events must be non-negative, got {n}"
            raise ValueError(msg)
        evt_id = _get_evt_id(parent)
        if p4 is None:
            momentum = EvtVector4R(EvtPDL.getMeanMass(evt_id), 0, 0, 0)
        else:
            momentum = EvtVector4R(*_as_four_vector(p4))
        # Other code, like phase_space(), may have installed another random engine
        EvtRandom.setRandomEngine(self.random_engine)
        events = []
        for _ in range(n):
            root = EvtParticleFactory.particleFactory(evt_id, momentum)
            try:
                root.setDiagonalSpinDensity()
                self.evtgen.generateDecay(root)
                events.append(Particle.from_evt_particle(root))
            finally:
                root.deleteTree()
        return events

    # The particle table only exists once EvtGen has been initialized
    def properties(self, particle: str | int) -> ParticleProperties:  # ruff: ignore[no-self-use]
        """Look up a particle by EvtGen name or PDG ID.

        Raises :code:`KeyError` if the particle is not in the particle table.

        >>> generator.properties(-511)
        ParticleProperties(name='anti-B0', pdg_id=-511, mass=5.279640)
        """
        return ParticleProperties.from_evt_id(_get_evt_id(particle))

    def particles(self) -> list[ParticleProperties]:  # ruff: ignore[no-self-use]
        """Return all entries of the particle table."""
        return [
            ParticleProperties.from_evt_id(EvtPDL.getEntry(i))
            for i in range(EvtPDL.entries())
        ]


def phase_space(
    parent_mass: float,
    masses: Sequence[float],
    n: int,
    seed: int | None = None,
) -> np.ndarray:
    r"""Generate unweighted :math:`n`-body phase space decays with EvtGen.

    This calls the :code:`EvtGenKine::PhaseSpace` routine directly with plain masses,
    so it needs no :class:`Generator`, particle table, or decay table. It can be used
    next to a :class:`Generator` and with different masses in one process.

    The routine uses accept-reject sampling, whose efficiency drops by about a factor
    of ten per additional daughter. Beyond about nine daughters it becomes impractically
    slow, and a running call cannot be interrupted.

    Args:
        parent_mass: Mass of the decaying state in GeV.
        masses: Masses of the 2 to 15 daughters in GeV.
        n: Number of events.
        seed: Seed for the random engine. A random seed is drawn if not given. Each
            call starts a new sequence, so use different seeds to extend a sample.

    Returns:
        Four-momenta :math:`(E, p_x, p_y, p_z)` in GeV in the rest frame of the parent
        with shape :code:`(n, len(masses), 4)`, with daughters in the order of
        :code:`masses`.

    >>> momenta = phase_space(3.097, [0.135, 0.14, 0.14], n=5, seed=0)
    >>> momenta.shape
    (5, 3, 4)
    >>> np.allclose(momenta.sum(axis=1), [3.097, 0, 0, 0])
    True
    """
    if n < 0:
        msg = f"Number of events must be non-negative, got {n}"
        raise ValueError(msg)
    if seed is None:
        seed = secrets.randbits(32)
    return _core.phase_space(parent_mass, list(masses), n, seed)


def final_state_momenta(events: Iterable[Particle]) -> np.ndarray:
    """Stack the final-state four-momenta of decay trees into one array.

    Returns:
        Array of shape :code:`(n_events, n_final_state, 4)` with the
        four-momenta :math:`(E, p_x, p_y, p_z)` in GeV.

    Raises:
        ValueError: If the events do not share the same final state, for
            instance because they decayed through different channels or
            radiated photons.
    """
    momenta = []
    expected_ids: list[int] | None = None
    for event in events:
        final_state = event.final_state()
        pdg_ids = [p.pdg_id for p in final_state]
        if expected_ids is None:
            expected_ids = pdg_ids
        elif pdg_ids != expected_ids:
            msg = (
                f"Events have different final states: {expected_ids} and {pdg_ids}."
                " Force a single decay channel with a user decay file and"
                " disable FSR to get a fixed final state."
            )
            raise ValueError(msg)
        momenta.append([p.p4 for p in final_state])
    if expected_ids is None:
        return np.empty((0, 0, 4))
    return np.array(momenta)


def _existing_file(path: str | os.PathLike) -> str:
    path = Path(path)
    if not path.is_file():
        msg = f"No such file: {path}"
        raise FileNotFoundError(msg)
    return str(path)


def _get_evt_id(particle: str | int) -> EvtId:
    if isinstance(particle, str):
        evt_id = EvtPDL.getId(particle)
        if evt_id.getId() < 0:
            msg = f"Unknown particle name {particle!r}"
            raise KeyError(msg)
        return evt_id
    evt_id = EvtPDL.evtIdFromStdHep(particle)
    if evt_id.getId() < 0:
        msg = f"Unknown PDG ID {particle}"
        raise KeyError(msg)
    return evt_id


def _as_four_vector(p4: Sequence[float]) -> tuple[float, float, float, float]:
    if len(p4) != 4:  # ruff: ignore[magic-value-comparison]
        msg = f"Four-momentum must have four components, got {len(p4)}"
        raise ValueError(msg)
    energy, px, py, pz = (float(x) for x in p4)
    return energy, px, py, pz
