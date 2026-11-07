// cspell:ignore Daug getctau ndarray ndim numpy
// Python bindings for EvtGen.
//
// EvtGen keeps its particle table, decay table and random engine in global
// state, so a process can hold only one Generator. Decay trees are copied into
// plain Particle values right after generation, so that Python never holds
// pointers into memory that EvtGen owns.

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/array.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/variant.h>
#include <nanobind/stl/vector.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <list>
#include <memory>
#include <mutex>
#include <optional>
#include <random>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

#include "EvtGen/EvtGen.hh"
#include "EvtGenBase/EvtGenKine.hh"
#include "EvtGenBase/EvtId.hh"
#include "EvtGenBase/EvtPDL.hh"
#include "EvtGenBase/EvtParticle.hh"
#include "EvtGenBase/EvtParticleFactory.hh"
#include "EvtGenBase/EvtRandom.hh"
#include "EvtGenBase/EvtRandomEngine.hh"
#include "EvtGenBase/EvtSpinType.hh"
#include "EvtGenBase/EvtVector4R.hh"
#include "EvtGenExternal/EvtExternalGenList.hh"

namespace nb = nanobind;
using namespace nb::literals;

using FourVector = std::array<double, 4>;
using ParticleKey = std::variant<int, std::string>;

namespace {

FourVector to_array(const EvtVector4R& v) {
    return {v.get(0), v.get(1), v.get(2), v.get(3)};
}

// Mersenne Twister engine; EvtGen's default engine is a 15-bit LCG.
class MersenneTwisterEngine : public EvtRandomEngine {
  public:
    explicit MersenneTwisterEngine(unsigned long seed) { setSeed(seed); }

    // EvtGen expects numbers in the open interval (0, 1)
    double random() override {
        double x;
        do {
            x = m_uniform(m_engine);
        } while (x == 0.0);
        return x;
    }

    void setSeed(unsigned long seed) override {
        m_seed = seed;
        m_engine.seed(seed);
        m_uniform.reset();
    }

    unsigned long lastSeed() const override { return m_seed; }

  private:
    std::mt19937_64 m_engine;
    std::uniform_real_distribution<double> m_uniform{0.0, 1.0};
    unsigned long m_seed = 0;
};

struct Particle {
    std::string name;
    int pdg_id;
    FourVector p4;
    FourVector position;
    double lifetime;
    int decay_mode;
    std::vector<Particle> daughters;

    double mass() const {
        const double m2 = p4[0] * p4[0] - p4[1] * p4[1] - p4[2] * p4[2] - p4[3] * p4[3];
        return m2 > 0.0 ? std::sqrt(m2) : 0.0;
    }

    void collect_final_state(std::vector<Particle>& out) const {
        if (daughters.empty()) {
            out.push_back(*this);
            return;
        }
        for (const auto& daughter : daughters) {
            daughter.collect_final_state(out);
        }
    }
};

Particle convert(EvtParticle* p) {
    const EvtId id = p->getId();
    Particle out{
        EvtPDL::name(id),
        EvtPDL::getStdHep(id),
        to_array(p->getP4Lab()),
        to_array(p->get4Pos()),
        p->getLifetime(),
        p->getNDaug() > 0 ? p->getChannel() : -1,
        {},
    };
    out.daughters.reserve(p->getNDaug());
    for (size_t i = 0; i < p->getNDaug(); ++i) {
        out.daughters.push_back(convert(p->getDaug(i)));
    }
    return out;
}

struct ParticleProperties {
    std::string name;
    int pdg_id;
    double mass;
    double width;
    double min_mass;
    double max_mass;
    double ctau;
    double charge;
    int spin2;
};

std::atomic<bool> g_initialized{false};

class Generator {
  public:
    Generator(const std::vector<std::string>& decay_files,
              const std::string& particle_table, const std::string& pythia_xml_dir,
              bool fsr, unsigned long seed, int mixing_type) {
        if (decay_files.empty()) {
            throw nb::value_error("At least one decay file is required");
        }
        if (g_initialized.exchange(true)) {
            throw std::runtime_error(
                "EvtGen has global state and can only be initialized once per "
                "process. Reuse the existing Generator instance.");
        }
        m_engine = std::make_unique<MersenneTwisterEngine>(seed);
        m_external = std::make_unique<EvtExternalGenList>(
            /*convertPythiaCodes=*/false, pythia_xml_dir, /*photonType=*/"gamma",
            /*useEvtGenRandom=*/true);
        if (fsr) {
            m_fsr.reset(m_external->getVinciaQEDModel());
        }
        const std::list<EvtDecayBase*> models = m_external->getListOfModels();
        m_evtgen = std::make_unique<EvtGen>(decay_files, particle_table, m_engine.get(),
                                            m_fsr.get(), &models, mixing_type);
    }

    void read_user_decay_file(const std::string& path) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_evtgen->readUDecay(path);
    }

    void set_seed(unsigned long seed) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_engine->setSeed(seed);
    }

    unsigned long seed() const { return m_engine->lastSeed(); }

    std::vector<Particle> generate(const ParticleKey& parent, size_t n,
                                   const std::optional<FourVector>& p4) {
        const EvtId id = lookup(parent);
        const EvtVector4R momentum =
            p4 ? EvtVector4R((*p4)[0], (*p4)[1], (*p4)[2], (*p4)[3])
               : EvtVector4R(EvtPDL::getMeanMass(id), 0.0, 0.0, 0.0);
        std::vector<Particle> events;
        events.reserve(n);
        nb::gil_scoped_release release;
        std::lock_guard<std::mutex> lock(m_mutex);
        // EvtRandom stores its engine in a thread-local pointer
        EvtRandom::setRandomEngine(m_engine.get());
        for (size_t i = 0; i < n; ++i) {
            EvtParticle* root = EvtParticleFactory::particleFactory(id, momentum);
            root->setDiagonalSpinDensity();
            m_evtgen->generateDecay(root);
            events.push_back(convert(root));
            root->deleteTree();
        }
        return events;
    }

    ParticleProperties properties(const ParticleKey& key) const {
        return properties_of(lookup(key));
    }

    std::vector<ParticleProperties> particles() const {
        std::vector<ParticleProperties> out;
        out.reserve(EvtPDL::entries());
        for (size_t i = 0; i < EvtPDL::entries(); ++i) {
            out.push_back(properties_of(EvtPDL::getEntry(static_cast<int>(i))));
        }
        return out;
    }

  private:
    static EvtId lookup(const ParticleKey& key) {
        if (const auto* name = std::get_if<std::string>(&key)) {
            const EvtId id = EvtPDL::getId(*name);
            if (id.getId() < 0) {
                throw nb::key_error(("Unknown particle name '" + *name + "'").c_str());
            }
            return id;
        }
        const int pdg_id = std::get<int>(key);
        const EvtId id = EvtPDL::evtIdFromStdHep(pdg_id);
        if (id.getId() < 0) {
            throw nb::key_error(("Unknown PDG ID " + std::to_string(pdg_id)).c_str());
        }
        return id;
    }

    static ParticleProperties properties_of(const EvtId& id) {
        return {
            EvtPDL::name(id),
            EvtPDL::getStdHep(id),
            EvtPDL::getMeanMass(id),
            EvtPDL::getWidth(id),
            EvtPDL::getMinMass(id),
            EvtPDL::getMaxMass(id),
            EvtPDL::getctau(id),
            EvtPDL::chg3(id) / 3.0,
            EvtSpinType::getSpin2(EvtPDL::getSpinType(id)),
        };
    }

    std::unique_ptr<MersenneTwisterEngine> m_engine;
    std::unique_ptr<EvtExternalGenList> m_external;
    std::unique_ptr<EvtAbsRadCorr> m_fsr;
    std::unique_ptr<EvtGen> m_evtgen;
    std::mutex m_mutex;
};

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
        static thread_local MersenneTwisterEngine engine(0);
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
    m.doc() = "Low-level bindings to the EvtGen C++ library.";
    m.attr("EVTGEN_VERSION") = PYEVTGEN_EVTGEN_VERSION;
    m.attr("HEPMC3_VERSION") = PYEVTGEN_HEPMC3_VERSION;
    m.attr("PYTHIA8_VERSION") = PYEVTGEN_PYTHIA8_VERSION;

    nb::class_<Particle>(m, "Particle",
                         "A particle in a generated decay tree.\n\n"
                         "Momenta are in GeV in the lab frame. Positions are in mm, "
                         "with the time component as c*t.")
        .def_ro("name", &Particle::name, "EvtGen particle name.")
        .def_ro("pdg_id", &Particle::pdg_id, "PDG Monte Carlo particle ID.")
        .def_ro("p4", &Particle::p4, "Four-momentum (E, px, py, pz) in GeV.")
        .def_ro("position", &Particle::position,
                "Production four-position (ct, x, y, z) in mm.")
        .def_ro("lifetime", &Particle::lifetime,
                "Sampled proper decay time as c*t in mm.")
        .def_ro("decay_mode", &Particle::decay_mode,
                "Index of the decay channel in the decay table, or -1 if the particle "
                "did not decay.")
        .def_ro("daughters", &Particle::daughters, "Direct decay products.")
        .def_prop_ro("mass", &Particle::mass, "Invariant mass of p4 in GeV.")
        .def(
            "final_state",
            [](const Particle& self) {
                std::vector<Particle> out;
                self.collect_final_state(out);
                return out;
            },
            "Return the stable particles at the leaves of the decay tree.")
        .def("__repr__", [](const Particle& self) {
            return "Particle(name='" + self.name +
                   "', pdg_id=" + std::to_string(self.pdg_id) +
                   ", n_daughters=" + std::to_string(self.daughters.size()) + ")";
        });

    nb::class_<ParticleProperties>(m, "ParticleProperties",
                                   "Entry of the EvtGen particle table (evt.pdl).")
        .def_ro("name", &ParticleProperties::name)
        .def_ro("pdg_id", &ParticleProperties::pdg_id)
        .def_ro("mass", &ParticleProperties::mass, "Nominal mass in GeV.")
        .def_ro("width", &ParticleProperties::width, "Width in GeV.")
        .def_ro("min_mass", &ParticleProperties::min_mass, "Lower mass cut-off in GeV.")
        .def_ro("max_mass", &ParticleProperties::max_mass, "Upper mass cut-off in GeV.")
        .def_ro("ctau", &ParticleProperties::ctau, "Mean proper decay length in mm.")
        .def_ro("charge", &ParticleProperties::charge, "Electric charge in units of e.")
        .def_ro("spin2", &ParticleProperties::spin2, "Twice the spin.")
        .def("__repr__", [](const ParticleProperties& self) {
            return "ParticleProperties(name='" + self.name +
                   "', pdg_id=" + std::to_string(self.pdg_id) +
                   ", mass=" + std::to_string(self.mass) + ")";
        });

    m.def("phase_space", &phase_space, "parent_mass"_a, "masses"_a, "n"_a, "seed"_a,
          "Generate n unweighted phase space decays in the parent rest frame.");

    nb::class_<Generator>(m, "Generator", "Wrapper around the EvtGen decay generator.")
        .def(nb::init<const std::vector<std::string>&, const std::string&,
                      const std::string&, bool, unsigned long, int>(),
             "decay_files"_a, "particle_table"_a, "pythia_xml_dir"_a, "fsr"_a, "seed"_a,
             "mixing_type"_a)
        .def("read_user_decay_file", &Generator::read_user_decay_file, "path"_a,
             "Read a user decay file that overrides entries of the main decay table.")
        .def_prop_ro("seed", &Generator::seed)
        .def("set_seed", &Generator::set_seed, "seed"_a)
        .def("generate", &Generator::generate, "parent"_a, "n"_a, "p4"_a = nb::none(),
             "Generate n decays of the parent particle, by default at rest.")
        .def("properties", &Generator::properties, "particle"_a,
             "Look up a particle by EvtGen name or PDG ID.")
        .def("particles", &Generator::particles,
             "Return all entries of the particle table.");
}
