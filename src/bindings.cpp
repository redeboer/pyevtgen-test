// cspell:ignore Daug ctau dotr getctau magr ndarray ndim numpy pdt scalartripler
// Python bindings for EvtGen.
//
// The classes and methods mirror the EvtGen C++ API one to one, with the same
// names, so that EvtGen's documentation and C++ examples carry over to Python.
// Python owns no EvtGen memory: as in C++, a particle tree that was created
// with EvtParticleFactory has to be released with EvtParticle.deleteTree().
//
// Only phase_space() goes beyond the C++ API, because looping over events in
// Python would be too slow for large samples.

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/operators.h>
#include <nanobind/stl/complex.h>
#include <nanobind/stl/list.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/tuple.h>
#include <nanobind/stl/vector.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <complex>
#include <list>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

#include "EvtGen/EvtGen.hh"
#include "EvtGenBase/EvtAbsRadCorr.hh"
#include "EvtGenBase/EvtComplex.hh"
#include "EvtGenBase/EvtDecayBase.hh"
#include "EvtGenBase/EvtDecayTable.hh"
#include "EvtGenBase/EvtGenKine.hh"
#include "EvtGenBase/EvtId.hh"
#include "EvtGenBase/EvtMTRandomEngine.hh"
#include "EvtGenBase/EvtPDL.hh"
#include "EvtGenBase/EvtParticle.hh"
#include "EvtGenBase/EvtParticleFactory.hh"
#include "EvtGenBase/EvtRandom.hh"
#include "EvtGenBase/EvtRandomEngine.hh"
#include "EvtGenBase/EvtSpinDensity.hh"
#include "EvtGenBase/EvtSpinType.hh"
#include "EvtGenBase/EvtVector4R.hh"
#include "EvtGenExternal/EvtExternalGenList.hh"

namespace nb = nanobind;
using namespace nb::literals;

namespace {

// EvtGen keeps its tables in global state and cannot be constructed twice
std::atomic<bool> g_evtgen_constructed{false};

void claim_evtgen() {
    if (g_evtgen_constructed.exchange(true)) {
        throw std::runtime_error(
            "EvtGen has global state and can only be initialized once per "
            "process. Reuse the existing EvtGen instance.");
    }
}

std::list<EvtDecayBase*> to_list(const std::vector<EvtDecayBase*>& models) {
    return {models.begin(), models.end()};
}

std::string to_string(const EvtVector4R& v) {
    std::ostringstream out;
    out << "EvtVector4R(" << v.get(0) << ", " << v.get(1) << ", " << v.get(2) << ", "
        << v.get(3) << ")";
    return out.str();
}

std::tuple<double, std::vector<EvtVector4R>> phase_space_kine(
    const std::vector<double>& masses, double parent_mass) {
    std::array<double, 30> mass{};
    std::array<EvtVector4R, 30> p4;
    if (masses.size() > mass.size()) {
        throw nb::value_error("EvtGenKine::PhaseSpace supports at most 30 daughters");
    }
    std::copy(masses.begin(), masses.end(), mass.begin());
    const double weight = EvtGenKine::PhaseSpace(static_cast<int>(masses.size()),
                                                 mass.data(), p4.data(), parent_mass);
    return {weight, {p4.begin(), p4.begin() + masses.size()}};
}

using MomentumArray = nb::ndarray<nb::numpy, double, nb::ndim<3>, nb::c_contig>;

MomentumArray phase_space(double parent_mass, const std::vector<double>& masses, size_t n,
                          unsigned long seed) {
    // EvtGenKine::PhaseSpace has no maximum weight for more daughters and takes
    // one-body decays to be at rest with the mass of the daughter.
    constexpr size_t max_daughters = 15;
    if (masses.size() < 2 || masses.size() > max_daughters) {
        throw nb::value_error("Phase space requires 2 to 15 daughters");
    }
    double mass_sum = 0.0;
    for (const double mass : masses) {
        if (!(mass >= 0.0)) {
            throw nb::value_error("Daughter masses must be non-negative");
        }
        mass_sum += mass;
    }
    if (!(parent_mass > mass_sum)) {
        throw nb::value_error("Parent mass must exceed the sum of the daughter masses");
    }
    const size_t n_daughters = masses.size();
    auto* data = new double[n * n_daughters * 4];
    nb::capsule owner(data, [](void* p) noexcept { delete[] static_cast<double*>(p); });
    {
        nb::gil_scoped_release release;
        // EvtRandom stores a thread-local pointer that outlives this function
        static thread_local EvtMTRandomEngine engine;
        engine.setSeed(seed);
        EvtRandom::setRandomEngine(&engine);
        std::array<double, 30> mass{};
        std::copy(masses.begin(), masses.end(), mass.begin());
        std::array<EvtVector4R, 30> p4;
        double* out = data;
        for (size_t i = 0; i < n; ++i) {
            EvtGenKine::PhaseSpace(static_cast<int>(n_daughters), mass.data(), p4.data(),
                                   parent_mass);
            for (size_t j = 0; j < n_daughters; ++j) {
                for (int k = 0; k < 4; ++k) {
                    *out++ = p4[j].get(k);
                }
            }
        }
    }
    return MomentumArray(data, {n, n_daughters, 4}, owner);
}

}  // namespace

NB_MODULE(_core, m) {
    m.doc() = "Bindings to the EvtGen C++ library, with the names of its C++ API.";
    m.attr("EVTGEN_VERSION") = PYEVTGEN_EVTGEN_VERSION;
    m.attr("HEPMC3_VERSION") = PYEVTGEN_HEPMC3_VERSION;
    m.attr("PYTHIA8_VERSION") = PYEVTGEN_PYTHIA8_VERSION;

    nb::class_<EvtId>(m, "EvtId",
                      "Identifier of a particle or alias in the EvtGen tables.")
        .def(nb::init<>())
        .def(nb::init<int, int>(), "id"_a, "alias"_a)
        .def("getId", &EvtId::getId)
        .def("getAlias", &EvtId::getAlias)
        .def("isAlias", &EvtId::isAlias)
        .def("isConjugate", &EvtId::isConjugate, "id"_a)
        .def("getName", &EvtId::getName)
        .def("__eq__",
             [](const EvtId& self, nb::handle other) {
                 return nb::isinstance<EvtId>(other) &&
                        self == nb::cast<const EvtId&>(other);
             })
        .def("__hash__",
             [](const EvtId& self) { return std::hash<int>()(self.getAlias()); })
        .def("__repr__", [](const EvtId& self) {
            return "EvtId(" + std::to_string(self.getId()) + ", " +
                   std::to_string(self.getAlias()) + ")";
        });

    nb::class_<EvtVector4R>(m, "EvtVector4R", "Four-vector (E, px, py, pz) in GeV.")
        .def(nb::init<>())
        .def(nb::init<double, double, double, double>(), "e"_a, "px"_a, "py"_a, "pz"_a)
        .def("get", &EvtVector4R::get, "i"_a)
        .def("set", nb::overload_cast<int, double>(&EvtVector4R::set), "i"_a, "d"_a)
        .def("set", nb::overload_cast<double, double, double, double>(&EvtVector4R::set),
             "e"_a, "px"_a, "py"_a, "pz"_a)
        .def("mass", &EvtVector4R::mass)
        .def("mass2", &EvtVector4R::mass2)
        .def("d3mag", &EvtVector4R::d3mag)
        .def("dot", &EvtVector4R::dot, "v2"_a,
             "Scalar product of the spatial components.")
        .def("cont", &EvtVector4R::cont, "v4"_a, "Minkowski scalar product.")
        .def("applyRotateEuler", &EvtVector4R::applyRotateEuler, "alpha"_a, "beta"_a,
             "gamma"_a)
        .def("applyBoostTo",
             nb::overload_cast<const EvtVector4R&, bool>(&EvtVector4R::applyBoostTo),
             "p4"_a, "inverse"_a = false)
        .def(nb::self + nb::self)
        .def(nb::self - nb::self)
        .def(nb::self * double())
        .def(double() * nb::self)
        .def(nb::self / double())
        .def(
            "__mul__", [](const EvtVector4R& a, const EvtVector4R& b) { return a * b; },
            nb::is_operator(), "Minkowski scalar product, as operator* in C++.")
        .def("__len__", [](const EvtVector4R&) { return 4; })
        .def("__iter__",
             [](const EvtVector4R& self) {
                 return nb::iter(
                     nb::make_tuple(self.get(0), self.get(1), self.get(2), self.get(3)));
             })
        .def("__getitem__",
             [](const EvtVector4R& self, int i) {
                 if (i < 0) {
                     i += 4;
                 }
                 if (i < 0 || i > 3) {
                     throw nb::index_error();
                 }
                 return self.get(i);
             })
        .def("__repr__", &to_string);
    m.def("boostTo",
          nb::overload_cast<const EvtVector4R&, const EvtVector4R&, bool>(&boostTo),
          "rs"_a, "p4"_a, "inverse"_a = false);
    m.def("rotateEuler", &rotateEuler, "rs"_a, "alpha"_a, "beta"_a, "gamma"_a);

    nb::class_<EvtSpinType> spin_type(m, "EvtSpinType");
    nb::enum_<EvtSpinType::spintype>(spin_type, "spintype")
        .value("SCALAR", EvtSpinType::SCALAR)
        .value("VECTOR", EvtSpinType::VECTOR)
        .value("TENSOR", EvtSpinType::TENSOR)
        .value("DIRAC", EvtSpinType::DIRAC)
        .value("PHOTON", EvtSpinType::PHOTON)
        .value("NEUTRINO", EvtSpinType::NEUTRINO)
        .value("STRING", EvtSpinType::STRING)
        .value("RARITASCHWINGER", EvtSpinType::RARITASCHWINGER)
        .value("SPIN3", EvtSpinType::SPIN3)
        .value("SPIN4", EvtSpinType::SPIN4)
        .value("SPIN5HALF", EvtSpinType::SPIN5HALF)
        .value("SPIN7HALF", EvtSpinType::SPIN7HALF)
        .export_values();
    spin_type.def_static("getSpin2", &EvtSpinType::getSpin2, "stype"_a)
        .def_static("getSpinStates", &EvtSpinType::getSpinStates, "stype"_a);

    nb::class_<EvtPDL>(m, "EvtPDL", "Particle data table, with static methods.")
        .def_static("getId", &EvtPDL::getId, "name"_a,
                    "Look up a particle by name. Returns EvtId(-1, -1) if it is unknown.")
        .def_static("name", &EvtPDL::name, "i"_a)
        .def_static("evtIdFromStdHep", &EvtPDL::evtIdFromStdHep, "stdhep"_a)
        .def_static("getStdHep", &EvtPDL::getStdHep, "id"_a)
        .def_static("chargeConj", &EvtPDL::chargeConj, "id"_a)
        .def_static("chg3", &EvtPDL::chg3, "i"_a)
        .def_static("getSpinType", &EvtPDL::getSpinType, "i"_a)
        .def_static("getMeanMass", &EvtPDL::getMeanMass, "i"_a)
        .def_static("getMass", &EvtPDL::getMass, "i"_a,
                    "Sample a mass from the line shape of the particle.")
        .def_static("getMinMass", &EvtPDL::getMinMass, "i"_a)
        .def_static("getMaxMass", &EvtPDL::getMaxMass, "i"_a)
        .def_static("getWidth", &EvtPDL::getWidth, "i"_a)
        .def_static("getctau", &EvtPDL::getctau, "i"_a)
        .def_static("entries", &EvtPDL::entries)
        .def_static("getEntry", &EvtPDL::getEntry, "i"_a)
        .def_static("reSetMass", &EvtPDL::reSetMass, "i"_a, "mass"_a)
        .def_static("reSetWidth", &EvtPDL::reSetWidth, "i"_a, "width"_a)
        .def_static("reSetMassMin", &EvtPDL::reSetMassMin, "i"_a, "mass"_a)
        .def_static("reSetMassMax", &EvtPDL::reSetMassMax, "i"_a, "mass"_a);

    nb::class_<EvtSpinDensity>(m, "EvtSpinDensity", "Spin density matrix.")
        .def(nb::init<>())
        .def("setDim", &EvtSpinDensity::setDim, "n"_a)
        .def("getDim", &EvtSpinDensity::getDim)
        .def("setDiag", &EvtSpinDensity::setDiag, "n"_a)
        .def(
            "set",
            [](EvtSpinDensity& self, int i, int j, std::complex<double> rho) {
                self.set(i, j, EvtComplex(rho.real(), rho.imag()));
            },
            "i"_a, "j"_a, "rhoij"_a)
        .def(
            "get",
            [](const EvtSpinDensity& self, int i, int j) {
                const EvtComplex& rho = self.get(i, j);
                return std::complex<double>(real(rho), imag(rho));
            },
            "i"_a, "j"_a)
        .def("normalizedProb", &EvtSpinDensity::normalizedProb, "d"_a);

    nb::class_<EvtParticle>(
        m, "EvtParticle",
        "Particle in an EvtGen decay tree.\n\n"
        "Create one with EvtParticleFactory.particleFactory() and release the tree "
        "with deleteTree() once it is no longer needed. As in C++, using a particle "
        "of a deleted tree is undefined behavior.")
        .def("getId", &EvtParticle::getId)
        .def("getName", &EvtParticle::getName)
        .def("getPDGId", &EvtParticle::getPDGId)
        .def("getSpinType", &EvtParticle::getSpinType)
        .def("getSpinStates", &EvtParticle::getSpinStates)
        .def("getP4", &EvtParticle::getP4,
             "Four-momentum in the rest frame of the parent.")
        .def("getP4Lab", &EvtParticle::getP4Lab)
        .def("getP4LabBeforeFSR", &EvtParticle::getP4LabBeforeFSR)
        .def("getP4Restframe", &EvtParticle::getP4Restframe)
        .def("get4Pos", &EvtParticle::get4Pos,
             "Production four-position (ct, x, y, z) in mm in the lab frame.")
        .def("getLifetime", &EvtParticle::getLifetime,
             "Sampled proper decay time as c*t in mm.")
        .def("mass", &EvtParticle::mass)
        .def("getNDaug", &EvtParticle::getNDaug)
        .def("getDaug", nb::overload_cast<const int>(&EvtParticle::getDaug), "i"_a,
             nb::rv_policy::reference)
        .def("getParent", &EvtParticle::getParent, nb::rv_policy::reference)
        .def("getChannel", &EvtParticle::getChannel)
        .def("isDecayed", &EvtParticle::isDecayed)
        .def("setDiagonalSpinDensity", &EvtParticle::setDiagonalSpinDensity)
        .def("setVectorSpinDensity", &EvtParticle::setVectorSpinDensity)
        .def("setSpinDensityForward", &EvtParticle::setSpinDensityForward, "rho"_a)
        .def("setSpinDensityForwardHelicityBasis",
             nb::overload_cast<const EvtSpinDensity&>(
                 &EvtParticle::setSpinDensityForwardHelicityBasis),
             "rho"_a)
        .def("getSpinDensityForward", &EvtParticle::getSpinDensityForward)
        .def("treeStr", &EvtParticle::treeStr)
        .def("printTree", &EvtParticle::printTree)
        .def("deleteTree", &EvtParticle::deleteTree,
             "Delete this particle and all its descendants.");

    nb::class_<EvtParticleFactory>(m, "EvtParticleFactory")
        .def_static(
            "particleFactory",
            nb::overload_cast<EvtId, EvtVector4R>(&EvtParticleFactory::particleFactory),
            "id"_a, "p4"_a, nb::rv_policy::reference,
            "Create a particle that is owned by the caller: release it with "
            "deleteTree().");

    nb::class_<EvtDecayBase>(m, "EvtDecayBase", "Decay model of one decay channel.")
        .def("getModelName", &EvtDecayBase::getModelName)
        .def("getParentId", &EvtDecayBase::getParentId)
        .def("getBranchingFraction", &EvtDecayBase::getBranchingFraction)
        .def("getNDaug", &EvtDecayBase::getNDaug)
        .def("getDaug", &EvtDecayBase::getDaug, "i"_a)
        .def("getNArg", &EvtDecayBase::getNArg)
        .def("getArgStr", &EvtDecayBase::getArgStr, "j"_a);

    nb::class_<EvtDecayTable>(m, "EvtDecayTable", "Decay tables that EvtGen has read.")
        .def_static("getInstance", &EvtDecayTable::getInstance, nb::rv_policy::reference)
        .def("getNDecayTables", &EvtDecayTable::getNDecayTables)
        .def("getNMode", &EvtDecayTable::getNMode, "ipar"_a, "tableIndex"_a = 0,
             "Number of decay channels of the particle with alias index ipar.")
        .def("getDecay", &EvtDecayTable::getDecay, "ipar"_a, "imode"_a,
             "tableIndex"_a = 0, nb::rv_policy::reference);

    nb::class_<EvtRandomEngine>(m, "EvtRandomEngine")
        .def("random", &EvtRandomEngine::random)
        .def("setSeed", &EvtRandomEngine::setSeed, "seed"_a)
        .def("lastSeed", &EvtRandomEngine::lastSeed);
    nb::class_<EvtMTRandomEngine, EvtRandomEngine>(m, "EvtMTRandomEngine",
                                                   "Mersenne Twister random engine.")
        .def(nb::init<unsigned long>(), "seed"_a = 1430957218);

    nb::class_<EvtRandom>(m, "EvtRandom")
        .def_static(
            "setRandomEngine",
            [](nb::object randomEngine) {
                // EvtRandom keeps a raw pointer, so keep the Python object alive
                EvtRandom::setRandomEngine(nb::cast<EvtRandomEngine*>(randomEngine));
                nb::module_::import_("pyevtgen._core").attr("_random_engine") =
                    randomEngine;
            },
            "randomEngine"_a)
        .def_static("Flat", nb::overload_cast<>(&EvtRandom::Flat))
        .def_static("Flat", nb::overload_cast<double>(&EvtRandom::Flat), "max"_a)
        .def_static("Flat", nb::overload_cast<double, double>(&EvtRandom::Flat), "min"_a,
                    "max"_a)
        .def_static("Gaussian", &EvtRandom::Gaussian);

    nb::class_<EvtGenKine>(m, "EvtGenKine")
        .def_static("PhaseSpace", &phase_space_kine, "mass"_a, "mp"_a,
                    "Generate one unweighted phase space decay. Returns the weight and "
                    "the daughter four-momenta, which C++ writes into its p4 argument.");

    nb::class_<EvtAbsRadCorr>(m, "EvtAbsRadCorr", "Engine for final-state radiation.");

    nb::class_<EvtExternalGenList>(m, "EvtExternalGenList",
                                   "Decay models and FSR engines of external generators.")
        .def(nb::init<bool, std::string, std::string, bool>(),
             "convertPythiaCodes"_a = false, "pythiaXmlDir"_a = "",
             "photonType"_a = "gamma", "useEvtGenRandom"_a = true)
        .def(
            "getListOfModels",
            [](EvtExternalGenList& self) {
                const std::list<EvtDecayBase*> models = self.getListOfModels();
                return std::vector<EvtDecayBase*>(models.begin(), models.end());
            },
            nb::rv_policy::reference)
        .def("getVinciaQEDModel", &EvtExternalGenList::getVinciaQEDModel,
             "infraredCutOff"_a = 1.0e-7, nb::rv_policy::reference);

    nb::class_<EvtGen>(m, "EvtGen",
                       "The EvtGen generator. Only one instance can exist per process.")
        .def(
            "__init__",
            [](EvtGen* self, const std::vector<std::string>& decayNames,
               const std::string& pdtTableName, EvtRandomEngine* randomEngine,
               EvtAbsRadCorr* isrEngine, const std::vector<EvtDecayBase*>& extraModels,
               int mixingType) {
                if (decayNames.empty()) {
                    throw nb::value_error("At least one decay file is required");
                }
                claim_evtgen();
                const std::list<EvtDecayBase*> models = to_list(extraModels);
                new (self) EvtGen(decayNames, pdtTableName, randomEngine, isrEngine,
                                  &models, mixingType);
            },
            "decayNames"_a, "pdtTableName"_a, "randomEngine"_a = nb::none(),
            "isrEngine"_a = nb::none(), "extraModels"_a = std::vector<EvtDecayBase*>{},
            "mixingType"_a = 1, nb::keep_alive<1, 4>(), nb::keep_alive<1, 5>())
        .def("readUDecay", &EvtGen::readUDecay, "udecay_name"_a, "useXml"_a = false)
        .def("generateDecay", nb::overload_cast<EvtParticle*>(&EvtGen::generateDecay),
             "p"_a);

    m.def("phase_space", &phase_space, "parent_mass"_a, "masses"_a, "n"_a, "seed"_a,
          "Generate n unweighted phase space decays in the parent rest frame.");
}
