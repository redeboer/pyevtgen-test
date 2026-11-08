"""Bindings to the EvtGen C++ library, with the names of its C++ API."""

from collections.abc import Iterator, Sequence
import enum
from typing import Annotated, overload

import numpy
from numpy.typing import NDArray


EVTGEN_VERSION: str = 'R03-01-00'

HEPMC3_VERSION: str = '3.3.1'

PYTHIA8_VERSION: str = '8318'

class EvtId:
    """Identifier of a particle or alias in the EvtGen tables."""

    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, id: int, alias: int) -> None: ...

    def getId(self) -> int: ...

    def getAlias(self) -> int: ...

    def isAlias(self) -> bool: ...

    def isConjugate(self, id: EvtId) -> bool: ...

    def getName(self) -> str: ...

    def __eq__(self, arg: object, /) -> bool: ...

    def __hash__(self) -> int: ...

    def __repr__(self) -> str: ...

class EvtVector4R:
    """Four-vector (E, px, py, pz) in GeV."""

    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self, e: float, px: float, py: float, pz: float) -> None: ...

    def get(self, i: int) -> float: ...

    @overload
    def set(self, i: int, d: float) -> None: ...

    @overload
    def set(self, e: float, px: float, py: float, pz: float) -> None: ...

    def mass(self) -> float: ...

    def mass2(self) -> float: ...

    def d3mag(self) -> float: ...

    def dot(self, v2: EvtVector4R) -> float:
        """Scalar product of the spatial components."""

    def cont(self, v4: EvtVector4R) -> float:
        """Minkowski scalar product."""

    def applyRotateEuler(self, alpha: float, beta: float, gamma: float) -> None: ...

    def applyBoostTo(self, p4: EvtVector4R, inverse: bool = False) -> None: ...

    def __add__(self, arg: EvtVector4R, /) -> EvtVector4R: ...

    def __sub__(self, arg: EvtVector4R, /) -> EvtVector4R: ...

    @overload
    def __mul__(self, arg: float, /) -> EvtVector4R: ...

    @overload
    def __mul__(self, arg: EvtVector4R, /) -> float:
        """Minkowski scalar product, as operator* in C++."""

    def __rmul__(self, arg: float, /) -> EvtVector4R: ...

    def __truediv__(self, arg: float, /) -> EvtVector4R: ...

    def __len__(self) -> int: ...

    def __iter__(self) -> Iterator: ...

    def __getitem__(self, arg: int, /) -> float: ...

    def __repr__(self) -> str: ...

def boostTo(rs: EvtVector4R, p4: EvtVector4R, inverse: bool = False) -> EvtVector4R: ...

def rotateEuler(rs: EvtVector4R, alpha: float, beta: float, gamma: float) -> EvtVector4R: ...

class EvtSpinType:
    class spintype(enum.Enum):
        SCALAR = 0

        VECTOR = 1

        TENSOR = 2

        DIRAC = 3

        PHOTON = 4

        NEUTRINO = 5

        STRING = 6

        RARITASCHWINGER = 7

        SPIN3 = 8

        SPIN4 = 9

        SPIN5HALF = 10

        SPIN7HALF = 11

    SCALAR: EvtSpinType.spintype = EvtSpinType.spintype.SCALAR

    VECTOR: EvtSpinType.spintype = EvtSpinType.spintype.VECTOR

    TENSOR: EvtSpinType.spintype = EvtSpinType.spintype.TENSOR

    DIRAC: EvtSpinType.spintype = EvtSpinType.spintype.DIRAC

    PHOTON: EvtSpinType.spintype = EvtSpinType.spintype.PHOTON

    NEUTRINO: EvtSpinType.spintype = EvtSpinType.spintype.NEUTRINO

    STRING: EvtSpinType.spintype = EvtSpinType.spintype.STRING

    RARITASCHWINGER: EvtSpinType.spintype = EvtSpinType.spintype.RARITASCHWINGER

    SPIN3: EvtSpinType.spintype = EvtSpinType.spintype.SPIN3

    SPIN4: EvtSpinType.spintype = EvtSpinType.spintype.SPIN4

    SPIN5HALF: EvtSpinType.spintype = EvtSpinType.spintype.SPIN5HALF

    SPIN7HALF: EvtSpinType.spintype = EvtSpinType.spintype.SPIN7HALF

    @staticmethod
    def getSpin2(stype: EvtSpinType.spintype) -> int: ...

    @staticmethod
    def getSpinStates(stype: EvtSpinType.spintype) -> int: ...

class EvtPDL:
    """Particle data table, with static methods."""

    @staticmethod
    def getId(name: str) -> EvtId:
        """Look up a particle by name. Returns EvtId(-1, -1) if it is unknown."""

    @staticmethod
    def name(i: EvtId) -> str: ...

    @staticmethod
    def evtIdFromStdHep(stdhep: int) -> EvtId: ...

    @staticmethod
    def getStdHep(id: EvtId) -> int: ...

    @staticmethod
    def chargeConj(id: EvtId) -> EvtId: ...

    @staticmethod
    def chg3(i: EvtId) -> int: ...

    @staticmethod
    def getSpinType(i: EvtId) -> EvtSpinType.spintype: ...

    @staticmethod
    def getMeanMass(i: EvtId) -> float: ...

    @staticmethod
    def getMass(i: EvtId) -> float:
        """Sample a mass from the line shape of the particle."""

    @staticmethod
    def getMinMass(i: EvtId) -> float: ...

    @staticmethod
    def getMaxMass(i: EvtId) -> float: ...

    @staticmethod
    def getWidth(i: EvtId) -> float: ...

    @staticmethod
    def getctau(i: EvtId) -> float: ...

    @staticmethod
    def entries() -> int: ...

    @staticmethod
    def getEntry(i: int) -> EvtId: ...

    @staticmethod
    def reSetMass(i: EvtId, mass: float) -> None: ...

    @staticmethod
    def reSetWidth(i: EvtId, width: float) -> None: ...

    @staticmethod
    def reSetMassMin(i: EvtId, mass: float) -> None: ...

    @staticmethod
    def reSetMassMax(i: EvtId, mass: float) -> None: ...

class EvtSpinDensity:
    """Spin density matrix."""

    def __init__(self) -> None: ...

    def setDim(self, n: int) -> None: ...

    def getDim(self) -> int: ...

    def setDiag(self, n: int) -> None: ...

    def set(self, i: int, j: int, rhoij: complex) -> None: ...

    def get(self, i: int, j: int) -> complex: ...

    def normalizedProb(self, d: EvtSpinDensity) -> float: ...

class EvtParticle:
    """
    Particle in an EvtGen decay tree.

    Create one with EvtParticleFactory.particleFactory() and release the tree with deleteTree() once it is no longer needed. As in C++, using a particle of a deleted tree is undefined behavior.
    """

    def getId(self) -> EvtId: ...

    def getName(self) -> str: ...

    def getPDGId(self) -> int: ...

    def getSpinType(self) -> EvtSpinType.spintype: ...

    def getSpinStates(self) -> int: ...

    def getP4(self) -> EvtVector4R:
        """Four-momentum in the rest frame of the parent."""

    def getP4Lab(self) -> EvtVector4R: ...

    def getP4LabBeforeFSR(self) -> EvtVector4R: ...

    def getP4Restframe(self) -> EvtVector4R: ...

    def get4Pos(self) -> EvtVector4R:
        """Production four-position (ct, x, y, z) in mm in the lab frame."""

    def getLifetime(self) -> float:
        """Sampled proper decay time as c*t in mm."""

    def mass(self) -> float: ...

    def getNDaug(self) -> int: ...

    def getDaug(self, i: int) -> EvtParticle: ...

    def getParent(self) -> EvtParticle: ...

    def getChannel(self) -> int: ...

    def isDecayed(self) -> bool: ...

    def setDiagonalSpinDensity(self) -> None: ...

    def setVectorSpinDensity(self) -> None: ...

    def setSpinDensityForward(self, rho: EvtSpinDensity) -> None: ...

    def setSpinDensityForwardHelicityBasis(self, rho: EvtSpinDensity) -> None: ...

    def getSpinDensityForward(self) -> EvtSpinDensity: ...

    def treeStr(self) -> str: ...

    def printTree(self) -> None: ...

    def deleteTree(self) -> None:
        """Delete this particle and all its descendants."""

class EvtParticleFactory:
    @staticmethod
    def particleFactory(id: EvtId, p4: EvtVector4R) -> EvtParticle:
        """
        Create a particle that is owned by the caller: release it with deleteTree().
        """

class EvtDecayBase:
    """Decay model of one decay channel."""

    def getModelName(self) -> str: ...

    def getParentId(self) -> EvtId: ...

    def getBranchingFraction(self) -> float: ...

    def getNDaug(self) -> int: ...

    def getDaug(self, i: int) -> EvtId: ...

    def getNArg(self) -> int: ...

    def getArgStr(self, j: int) -> str: ...

class EvtDecayTable:
    """Decay tables that EvtGen has read."""

    @staticmethod
    def getInstance() -> EvtDecayTable: ...

    def getNDecayTables(self) -> int: ...

    def getNMode(self, ipar: int, tableIndex: int = 0) -> int:
        """Number of decay channels of the particle with alias index ipar."""

    def getDecay(self, ipar: int, imode: int, tableIndex: int = 0) -> EvtDecayBase: ...

class EvtRandomEngine:
    def random(self) -> float: ...

    def setSeed(self, seed: int) -> None: ...

    def lastSeed(self) -> int: ...

class EvtMTRandomEngine(EvtRandomEngine):
    """Mersenne Twister random engine."""

    def __init__(self, seed: int = 1430957218) -> None: ...

class EvtRandom:
    @staticmethod
    def setRandomEngine(randomEngine: object) -> None: ...

    @overload
    @staticmethod
    def Flat() -> float: ...

    @overload
    @staticmethod
    def Flat(max: float) -> float: ...

    @overload
    @staticmethod
    def Flat(min: float, max: float) -> float: ...

    @staticmethod
    def Gaussian() -> float: ...

class EvtGenKine:
    @staticmethod
    def PhaseSpace(mass: Sequence[float], mp: float) -> tuple[float, list[EvtVector4R]]:
        """
        Generate one unweighted phase space decay. Returns the weight and the daughter four-momenta, which C++ writes into its p4 argument.
        """

class EvtAbsRadCorr:
    """Engine for final-state radiation."""

class EvtExternalGenList:
    """Decay models and FSR engines of external generators."""

    def __init__(self, convertPythiaCodes: bool = False, pythiaXmlDir: str = '', photonType: str = 'gamma', useEvtGenRandom: bool = True) -> None: ...

    def getListOfModels(self) -> list[EvtDecayBase]: ...

    def getVinciaQEDModel(self, infraredCutOff: float = 1e-07) -> EvtAbsRadCorr: ...

class EvtGen:
    """The EvtGen generator. Only one instance can exist per process."""

    def __init__(self, decayNames: Sequence[str], pdtTableName: str, randomEngine: EvtRandomEngine | None = None, isrEngine: EvtAbsRadCorr | None = None, extraModels: Sequence[EvtDecayBase] = [], mixingType: int = 1) -> None: ...

    def readUDecay(self, udecay_name: str, useXml: bool = False) -> None: ...

    def generateDecay(self, p: EvtParticle) -> None: ...

def phase_space(parent_mass: float, masses: Sequence[float], n: int, seed: int) -> Annotated[NDArray[numpy.float64], dict(shape=(None, None, None), order='C')]:
    """Generate n unweighted phase space decays in the parent rest frame."""
