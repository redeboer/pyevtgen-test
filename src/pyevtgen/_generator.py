"""Python interface to the EvtGen generator and its bundled data files."""

# cspell:ignore Mersenne

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from pyevtgen import _core
from pyevtgen._core import Generator as _CoreGenerator

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from pyevtgen._core import Particle, ParticleProperties

DATA_DIR = Path(_core.__file__).parent / "data"
DECAY_FILE = DATA_DIR / "DECAY.DEC"
"""Default EvtGen decay table that is bundled with the package."""
PARTICLE_TABLE = DATA_DIR / "evt.pdl"
"""Default EvtGen particle table that is bundled with the package."""
PYTHIA8_XML_DIR = DATA_DIR / "pythia8" / "xmldoc"
"""Pythia8 settings and particle data, used by EvtGen's ``PYTHIA`` decay model."""


class Generator:
    """EvtGen decay generator.

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
        self.__core = _CoreGenerator(
            decay_files,
            _existing_file(particle_table),
            str(PYTHIA8_XML_DIR),
            fsr,
            seed,
            mixing_type,
        )
        if user_decay_file is not None:
            self.read_user_decay_file(user_decay_file)

    @property
    def seed(self) -> int:
        """Seed with which the random engine was last initialized."""
        return self.__core.seed

    @seed.setter
    def seed(self, value: int) -> None:
        self.__core.set_seed(value)

    def read_user_decay_file(self, path: str | os.PathLike) -> None:
        """Override entries of the decay table with those of a user decay file."""
        self.__core.read_user_decay_file(_existing_file(path))

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
        return self.__core.generate(parent, n, _as_four_vector(p4))

    def properties(self, particle: str | int) -> ParticleProperties:
        """Look up a particle by EvtGen name or PDG ID.

        Raises :code:`KeyError` if the particle is not in the particle table.

        >>> generator.properties(-511)
        ParticleProperties(name='anti-B0', pdg_id=-511, mass=5.279640)
        """
        return self.__core.properties(particle)

    def particles(self) -> list[ParticleProperties]:
        """Return all entries of the particle table."""
        return self.__core.particles()


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


def _as_four_vector(p4: Sequence[float] | None) -> tuple[float, ...] | None:
    if p4 is None:
        return None
    if len(p4) != 4:  # ruff: ignore[magic-value-comparison]
        msg = f"Four-momentum must have four components, got {len(p4)}"
        raise ValueError(msg)
    return tuple(float(x) for x in p4)
