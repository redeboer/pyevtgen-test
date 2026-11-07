# cspell:ignore fjcore fsigned inlines licence sabi skbuild xmldir
cmake_minimum_required(VERSION 3.24...4.0)
project(${SKBUILD_PROJECT_NAME} VERSION ${SKBUILD_PROJECT_VERSION} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_VISIBILITY_PRESET hidden)
set(CMAKE_VISIBILITY_INLINES_HIDDEN ON)

# Upstream sources are downloaded at configure time. They are compiled directly
# into static libraries instead of through their own build systems: EvtGen's
# CMake requires ROOT, which the library itself does not use, Pythia8 uses a
# hand-written configure script, and all would otherwise install shared
# libraries and headers into the wheel. The non-existent SOURCE_SUBDIR makes
# FetchContent download without calling add_subdirectory().
include(FetchContent)
set(PYEVTGEN_HEPMC3_VERSION 3.3.1)
set(PYEVTGEN_PYTHIA8_VERSION 8318)
set(PYEVTGEN_EVTGEN_TAG R03-01-00)
FetchContent_Declare(
  hepmc3
  URL https://hepmc.web.cern.ch/hepmc/releases/HepMC3-${PYEVTGEN_HEPMC3_VERSION}.tar.gz
  URL_HASH SHA256=08240160b0f28dc3293aa4d61ce65e2d67cd597acf6faca439f2e46625f7e793
  SOURCE_SUBDIR do-not-add
  DOWNLOAD_EXTRACT_TIMESTAMP ON
)
FetchContent_Declare(
  pythia8
  URL https://pythia.org/releases/pythia83/pythia${PYEVTGEN_PYTHIA8_VERSION}.tgz
  URL_HASH SHA256=85dce1e623f91499b2973e3f939bf760b0f745ad4f4eb1bd0fbce2074e2e8f5c
  SOURCE_SUBDIR do-not-add
  DOWNLOAD_EXTRACT_TIMESTAMP ON
)
FetchContent_Declare(
  evtgen
  URL https://gitlab.cern.ch/evtgen/evtgen/-/archive/${PYEVTGEN_EVTGEN_TAG}/evtgen-${PYEVTGEN_EVTGEN_TAG}.tar.gz
  URL_HASH SHA256=91f247397196d71b11ae92b697a51e1bc483ecfdf2d3a4ef6b78a125bfc72aad
  SOURCE_SUBDIR do-not-add
  DOWNLOAD_EXTRACT_TIMESTAMP ON
)
FetchContent_MakeAvailable(hepmc3 pythia8 evtgen)

file(GLOB HEPMC3_SOURCES CONFIGURE_DEPENDS ${hepmc3_SOURCE_DIR}/src/*.cc)
add_library(hepmc3_static STATIC ${HEPMC3_SOURCES})
target_include_directories(hepmc3_static SYSTEM PUBLIC ${hepmc3_SOURCE_DIR}/include)
target_compile_definitions(hepmc3_static PUBLIC HEPMC3_NO_EXPORTS)
target_link_libraries(hepmc3_static PUBLIC ${CMAKE_DL_LIBS})

file(GLOB PYTHIA8_SOURCES CONFIGURE_DEPENDS ${pythia8_SOURCE_DIR}/src/*.cc)
add_library(pythia8_static STATIC ${PYTHIA8_SOURCES})
target_include_directories(pythia8_static SYSTEM PUBLIC ${pythia8_SOURCE_DIR}/include)
target_link_libraries(pythia8_static PUBLIC ${CMAKE_DL_LIBS})
# Mirror the per-file flags of Pythia8's Makefile. XMLDIR is only a fallback:
# the bindings always pass the bundled xmldoc directory explicitly.
set_source_files_properties(
  ${pythia8_SOURCE_DIR}/src/Pythia.cc PROPERTIES COMPILE_DEFINITIONS XMLDIR=""
)
set_source_files_properties(
  ${pythia8_SOURCE_DIR}/src/FJcore.cc
  PROPERTIES COMPILE_DEFINITIONS FJCORE_HAVE_LIMITED_THREAD_SAFETY
)

# Photos++, Tauola++ and Sherpa are not linked; their interface classes in
# EvtGenExternal compile to stubs. Pythia8 provides the PYTHIA decay model, which
# the default decay table needs, and Vincia QED for final-state radiation.
file(
  GLOB EVTGEN_SOURCES CONFIGURE_DEPENDS
  ${evtgen_SOURCE_DIR}/src/EvtGen.cpp
  ${evtgen_SOURCE_DIR}/src/EvtGenBase/*.cpp
  ${evtgen_SOURCE_DIR}/src/EvtGenModels/*.cpp
  ${evtgen_SOURCE_DIR}/src/EvtGenExternal/*.cpp
)
add_library(evtgen_static STATIC ${EVTGEN_SOURCES})
target_include_directories(evtgen_static SYSTEM PUBLIC ${evtgen_SOURCE_DIR})
target_compile_definitions(evtgen_static PUBLIC EVTGEN_HEPMC3 EVTGEN_PYTHIA EVTGEN_VINCIA)
target_link_libraries(evtgen_static PUBLIC hepmc3_static pythia8_static)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  # EvtGen assumes a signed char (see EvtGenCompilerFlags.cmake upstream)
  target_compile_options(evtgen_static PUBLIC -fsigned-char)
  target_compile_options(evtgen_static PRIVATE -w)
  target_compile_options(hepmc3_static PRIVATE -w)
  target_compile_options(pythia8_static PRIVATE -w)
endif()

find_package(
  Python 3.10 REQUIRED
  COMPONENTS Interpreter Development.Module ${SKBUILD_SABI_COMPONENT}
)
find_package(nanobind CONFIG REQUIRED)
nanobind_add_module(_core STABLE_ABI NB_STATIC src/bindings.cpp)
target_link_libraries(_core PRIVATE evtgen_static)
target_compile_definitions(
  _core PRIVATE
  PYEVTGEN_EVTGEN_VERSION="${PYEVTGEN_EVTGEN_TAG}"
  PYEVTGEN_HEPMC3_VERSION="${PYEVTGEN_HEPMC3_VERSION}"
  PYEVTGEN_PYTHIA8_VERSION="${PYEVTGEN_PYTHIA8_VERSION}"
)
# Editor support for local builds in build/{wheel_tag}: clangd reads
# build/compile_commands.json. nanobind's headers are copied, because uv deletes
# the isolated build environment that they come from after the build.
cmake_path(IS_PREFIX CMAKE_SOURCE_DIR ${CMAKE_BINARY_DIR} PYEVTGEN_LOCAL_BUILD)
if(PYEVTGEN_LOCAL_BUILD)
  set_target_properties(_core PROPERTIES EXPORT_COMPILE_COMMANDS ON)
  file(COPY ${NB_DIR}/include/ DESTINATION ${CMAKE_BINARY_DIR}/nanobind-include)
  target_include_directories(_core BEFORE PRIVATE ${CMAKE_BINARY_DIR}/nanobind-include)
  file(
    CREATE_LINK ${CMAKE_BINARY_DIR}/compile_commands.json
    ${CMAKE_SOURCE_DIR}/build/compile_commands.json SYMBOLIC
  )
endif()

# The stub is written into the source tree and committed, so that type checkers
# can resolve pyevtgen._core without a build. Every build regenerates it.
nanobind_add_stub(
  _core_stub
  MODULE _core
  OUTPUT ${CMAKE_CURRENT_SOURCE_DIR}/src/pyevtgen/_core.pyi
  PYTHON_PATH $<TARGET_FILE_DIR:_core>
  DEPENDS _core
)

install(TARGETS _core LIBRARY DESTINATION pyevtgen)
install(
  FILES ${evtgen_SOURCE_DIR}/DECAY.DEC ${evtgen_SOURCE_DIR}/evt.pdl
  DESTINATION pyevtgen/data
)
# Pythia8 resolves tunes/ relative to xmldoc/
install(
  DIRECTORY ${pythia8_SOURCE_DIR}/share/Pythia8/xmldoc ${pythia8_SOURCE_DIR}/share/Pythia8/tunes
  DESTINATION pyevtgen/data/pythia8
)

# EvtGen and Pythia8 are GPL, HepMC3 is LGPL; ship their licenses in the wheel
install(
  FILES ${evtgen_SOURCE_DIR}/COPYING
  DESTINATION ${SKBUILD_METADATA_DIR}/licenses/EvtGen
)
install(
  FILES ${hepmc3_SOURCE_DIR}/LICENCE ${hepmc3_SOURCE_DIR}/COPYING
  DESTINATION ${SKBUILD_METADATA_DIR}/licenses/HepMC3
)
install(
  FILES ${pythia8_SOURCE_DIR}/COPYING
  DESTINATION ${SKBUILD_METADATA_DIR}/licenses/Pythia8
)
