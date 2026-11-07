"""Python bindings for the EvtGen particle decay generator.

The package ships a statically linked build of `EvtGen
<https://gitlab.cern.ch/evtgen/evtgen>`_ together with its default decay table
(:data:`DECAY_FILE`) and particle table (:data:`PARTICLE_TABLE`).

>>> generator = Generator(seed=42)  # doctest: +SKIP
>>> event = generator.decay("D*+")
>>> event.name, event.pdg_id
('D*+', 413)
>>> all(not p.daughters for p in event.final_state())
True
"""

from pyevtgen._core import (
    EVTGEN_VERSION,
    HEPMC3_VERSION,
    PYTHIA8_VERSION,
    Particle,
    ParticleProperties,
)
from pyevtgen._generator import (
    DECAY_FILE,
    PARTICLE_TABLE,
    PYTHIA8_XML_DIR,
    Generator,
    final_state_momenta,
    phase_space,
)

__all__ = [
    "DECAY_FILE",
    "EVTGEN_VERSION",
    "HEPMC3_VERSION",
    "PARTICLE_TABLE",
    "PYTHIA8_VERSION",
    "PYTHIA8_XML_DIR",
    "Generator",
    "Particle",
    "ParticleProperties",
    "final_state_momenta",
    "phase_space",
]
