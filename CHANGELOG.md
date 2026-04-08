# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Fresh-install validation notes

The following was observed when running `bash install.sh --with-ppc` from a
fully clean state (no conda environment, no micromamba binary, no pre-built
packages):

**Step 1 — Environment creation (`setup_env.sh`)**
Micromamba is downloaded by `setup_env.sh` and stored in `bin/`.  This requires
an internet connection.  All 189 conda-forge packages are resolved and linked
(~5 min on first run; subsequent runs use the local `pkgs/` cache and are
near-instant).

**Step 2 — PROPOSAL (`install_proposal.sh`)**
Built from source via pip (~2 min).  This requires a working C++ tool-chain
(`g++`).  Watch for pip backtracking warnings during the prometheus editable
install step — they are harmless but can take several minutes while pip
searches for compatible versions of `flax` / `orbax-checkpoint`.

**Step 3 — LeptonInjector (`install_leptoninjector_legacy.sh`)**
Built from the vendored source at `resources/LeptonInjector/` (no network
access required). Compiled with CMake/GCC (~3 min). CMake emits a non-fatal
warning about `PYTHON_EXECUTABLE` being ignored (use `Python_ROOT_DIR`
instead) and two `CMP0074` policy warnings about `HDF5_ROOT`; these do
**not** affect the build.

**Step 4 — PPC (`install_ppc.sh`, requires `--with-ppc`)**
The symlinks `ppc.cxx → ppc.cu` and `pro.cxx → pro.cu` already exist in the
repo, so `ln -s` prints a "File exists" warning; this is harmless.

**Step 5 — Prometheus pip install (`fixes.sh`)**
Installs prometheus in editable mode and then installs `fennel-seed 2.0.0`
from the vendored source at `resources/fennel/` (no network access required).
Pip will downgrade `numpy` from 2.x to 1.26.4 and `jax`/`jaxlib` from 0.9.2
to 0.4.35 to satisfy pinned versions in `pyproject.toml`.

**First run of either example**
PROPOSAL builds its cross-section/decay tables on the first simulation run
and writes them to `resources/PROPOSAL_tables/`. This takes ~1–2 min and only
happens once. A precision warning from the PROPOSAL integrator is printed but
is purely informational. A `FutureWarning` from JAX about dtype promotion is
also non-fatal.

---

## [Unreleased] — branch `smb-version2`

### Added

- **`install.sh`** — top-level installer script that orchestrates the full
  environment setup in the correct order:
  `setup_env.sh` → `activate.sh` → `install_proposal.sh` →
  `install_leptoninjector_legacy.sh` → (optional) `install_ppc.sh` →
  `check_install.sh` → `fixes.sh`.
  Accepts `--with-ppc` flag to opt in to building the CPU PPC binary.

- **`scripts/setup_env.sh`** — downloads micromamba and creates the conda
  environment defined in `environment.yml`.

- **`scripts/activate.sh`** — activates the conda environment for a given
  environment directory.

- **`scripts/install_proposal.sh`** — installs the PROPOSAL lepton propagator
  via pip into the active environment.

- **`scripts/install_leptoninjector_legacy.sh`** — builds and installs
  LeptonInjector from the vendored source at `resources/LeptonInjector/`
  using CMake (no network access required).

- **`scripts/install_ppc.sh`** — compiles the CPU-only PPC photon propagator
  binary (`resources/PPC_executables/PPC/ppc`) from source using `g++ -O2
  --fast-math`.

- **`scripts/check_install.sh`** — verifies that all key Python packages
  (`LeptonInjector`, `EarthModelService`, `proposal`, `prometheus`) import
  without errors after installation.

- **`scripts/fixes.sh`** — runs `pip install -e .` to install prometheus in
  editable mode and installs fennel-seed 2.0.0 from the vendored source at
  `resources/fennel/`.

- **`resources/LeptonInjector/`** — vendored copy of the
  `icecube/LeptonInjector` `with_earth_py` branch (commit `d203189b`,
  Feb 2023, LGPL-3.0). All four GCC 13 / SuiteSparse 7.x compatibility
  patches are baked in. Protects against upstream branch deletion and removes
  the GitHub clone step from installation.

- **`resources/fennel/`** — vendored copy of fennel-seed 2.0.0 (commit
  `988bf2f`, MIT license). fennel-seed 2.0.0 is not published on PyPI;
  previously installed from GitHub at install time. The `notebooks/` and
  `seed/` directories are excluded as they are not needed at runtime.

- **`resources/PPC_executables/PPC/ppc`** — compiled CPU PPC binary, produced
  by `scripts/install_ppc.sh`.

- **`examples/01_basic_water.py`** — minimal end-to-end example for a water
  detector simulation.  Uses the bundled `resources/geofiles/demo_water.geo`,
  a single-event LeptonInjector volume injection of a muon neutrino CC
  interaction, and the olympus photon propagator.  Writes output to
  `output/1_photons.parquet`.

- **`examples/02_basic_ice.py`** — minimal end-to-end example for an ice
  detector simulation (PPC).  Uses the bundled
  `resources/geofiles/demo_ice.geo` and the south-pole PPC ice tables in
  `resources/PPC_tables/south_pole/`.  Runs 3 events with a volume-injected
  muon and writes output to `output/2_photons.parquet`.

### Fixed

- **`install.sh`** — added `export PATH="${PWD}/bin:${PATH}"` so the
  repo-local micromamba binary (downloaded by `setup_env.sh`) is visible to
  all sub-scripts that are invoked as separate `bash` processes.

- **`scripts/install_leptoninjector_legacy.sh`** — rewritten to build from
  `resources/LeptonInjector/` instead of cloning from GitHub. The four
  source-level GCC 13 / SuiteSparse 7.x compatibility patches (originally
  applied at build time) are now baked into the vendored tree:
  - `cmake/Packages/SuiteSparse.cmake`: replaced a `STRING(REGEX REPLACE)` on
    the entire header file content (which contains dots and newlines, breaking
    CMake 3.22 regex matching) with a `STRING(REGEX MATCH)` + conditional so
    that the major version number is extracted reliably.
  - `public/LeptonInjector/Coordinates.h`: added `#include <cstdint>` to fix
    a missing declaration of `uint8_t` under GCC 13 (which no longer includes
    `<cstdint>` transitively).
  - `public/LeptonInjector/Particle.h`: same `#include <cstdint>` fix.
  - `private/LeptonInjector/Particle.cxx`: added `#include <stdexcept>` to
    fix a missing declaration of `std::runtime_error` under GCC 13.
  - Fixed `$PYTHONPATH` unbound-variable error (triggered by `set -u`) by
    changing to `${PYTHONPATH:-}`.

- **`scripts/fixes.sh`** — updated fennel install from
  `git+https://github.com/MeighenBergerS/fennel.git@master` to the vendored
  `resources/fennel/` path.

- **`prometheus/utils/config_mims.py`** (`config_mims`): added
  `os.makedirs(os.path.dirname(output_prefix), exist_ok=True)` so that
  LeptonInjector's output directory is created automatically.  Previously the
  simulation crashed with "Failed to open … .lic" when the `output/` directory
  did not exist.

- **`prometheus/utils/config_mims.py`** (`config_mims`): fixed the call to
  `photon_prop_config_mims` — it was passing
  `config["photon propagator"][name]` (the propagator-specific sub-dict) but
  the function signature expects the full `config["photon propagator"]` dict
  so it can read the `"name"` key.

- **`prometheus/utils/config_mims.py`** (`photon_prop_config_mims`): replaced
  the `pass` stub with a real implementation.  Resolves relative `ppctables`,
  `ppc_exe`, and `ppc_tmpdir` paths in the PPC/PPC_CUDA config to absolute
  paths.  Relative paths are interpreted as relative to the `prometheus`
  package directory (`prometheus/prometheus/`) so they work regardless of the
  process working directory.

---

## Phase 0 — Safety net (tests, CI, macOS compatibility)

### Added

#### Test suite

- **`tests/conftest.py`** — pytest session configuration.  `chdir`s to the
  repository root at session start so all path-relative operations work
  regardless of where `pytest` is invoked.  Adds a `--run-slow` CLI option
  and a collection hook that automatically skips any test marked `slow` unless
  that flag is passed.

- **`tests/test_smoke.py`** — import smoke tests for all 20 live sub-modules
  across `prometheus`, `hyperion`, and `olympus`.  Runs in under 5 seconds.
  One `xfail` marks `prometheus.weighting` (requires the optional
  `LeptonWeighter` package which is not a declared dependency).

- **`tests/test_e2e.py`** — end-to-end physics regression test
  (`@pytest.mark.slow`).  Runs a 100-event water simulation with seed 42 and
  asserts that the total photon hit count stays within ±1 % of the baseline
  value (25 193 hits).  Isolated via `tmp_path` so it never writes to the
  working tree.  Activated with `pytest --run-slow`.

- **`tests/test_utils.py`** — 48 unit tests covering `units`, `iter_or_rep`,
  `convert_loss_name`, the PDG/f2k/pstring translator dictionaries,
  `path_length_sampling`, `find_cog`, and `ExtendedEnum`.

- **`tests/test_dataclasses.py`** — 67 unit tests covering `Particle`,
  `PropagatableParticle`, `Loss`, `Hit`, `Interactions`, `MCRecord`,
  `PhotonSource`, `should_propagate`, and `accumulate_hits`.

- **`tests/test_detector_unit.py`** — 43 unit tests covering `Module`,
  `Medium`, `Detector` (construction, key lookup, addition, geometry
  properties), `make_line`, `make_grid`, and `detector_from_geo`.

- **`tests/test_geo.py`** — 18 unit tests covering `from_geo` (water, ice,
  IceCube, and P-One geofiles) and a full write-then-read round-trip for
  `geo_from_coords`.

- **`pyproject.toml`** — added `[tool.pytest.ini_options]` block:
  `testpaths = ["tests"]` and `markers = ["slow: ..."]` so pytest discovers
  tests without any path arguments and the `slow` marker is registered (no
  `PytestUnknownMarkWarning`).

- **`scripts/fixes.sh`** — added `pip install pytest` so pytest is available
  immediately after installation without any manual step.

- **`.github/workflows/ci.yml`** — GitHub Actions CI workflow that runs on
  every push and pull request to any branch.  Installs prometheus via
  `install.sh` and runs the fast test suite (`python -m pytest --tb=short
  -q`).  The slow e2e tests are intentionally excluded from CI (~8 min
  runtime) and must be run locally before merging changes that touch the
  simulation pipeline.

#### macOS compatibility

- **`scripts/setup_env.sh`** — platform detection (`uname -s` + `uname -m`)
  to select the correct micromamba binary for `linux-64`, `linux-aarch64`,
  `osx-64`, or `osx-arm64`.  The executability check now uses
  `"${PWD}/bin/micromamba" --version` instead of a plain `[ -f … ]` test.

- **`scripts/activate.sh`** — removed the `realpath -m` call (GNU-only,
  absent on macOS BSD `realpath`).  Shell detection now reads `$SHELL` and
  selects the correct micromamba hook for `zsh` or `bash`.

- **`scripts/install_leptoninjector_legacy.sh`** — replaced `wget` with
  `curl -fsSL` (wget is not installed by default on macOS).  Replaced
  `$(nproc)` with `$(nproc 2>/dev/null || sysctl -n hw.logicalcpu)` in both
  `make -j` invocations to work on macOS.

- **`scripts/install_ppc.sh`** — added an early exit on macOS (`uname -s ==
  Darwin`) with a clear message; PPC requires CUDA and is Linux-only.

- **`INSTALL_NOTES.md`** — Quick Start section, platform compatibility table,
  macOS-specific notes, and a known-limitations table.

#### Repository hygiene

- **`.gitignore`** — added `PROPOSAL_tables/`, `*.f2k`, `*.ppc`,
  `__pycache__/`, and `*.egg-info/` to prevent generated files from being
  accidentally committed.

### Removed

- **`tests/test_gvd.py`** and **`tests/test_icecube_gen2.py`** — both tests
  imported from the legacy `hebe` package which is no longer installed.
  Deleted rather than left as permanently broken skips.

### Fixed

- **`tests/test_pone.py`**, **`tests/test_icecube.py`**,
  **`tests/test_injection.py`** — removed `sys.path.append("..")` hacks;
  all paths are now relative to the repository root (via the `conftest.py`
  `chdir`).  Geofile paths updated from `../prometheus/data/` to
  `resources/geofiles/`.

- **`tests/test_icecube.py`** — updated `outer_cylinder` and `outer_radius`
  expected values to match the current IceCube geofile geometry computation
  (`outer_cylinder = [596.28, 1037.38]`, `outer_radius = 789.82`).

---

## macOS removal & Docker support

### Added

#### Docker

- **`container/Dockerfile`** — self-contained CPU image based on
  `ubuntu:22.04`.  Six-stage multi-stage build:
  `base` (system packages + micromamba + conda env) →
  `proposal` (pip install + pre-build PROPOSAL interpolation tables) →
  `leptoninjector` (CMake build from vendored `resources/LeptonInjector/`) →
  `ppc` (`make cpu` from vendored `resources/PPC_executables/PPC/`) →
  `prometheus_install` (fennel + prometheus editable install) →
  `final` (ENV vars + import smoke test).
  Build: `docker build -f container/Dockerfile -t prometheus:cpu .`
  (from repo root).

- **`container/Dockerfile.gpu`** — GPU/CUDA variant based on
  `nvidia/cuda:12.3.2-devel-ubuntu22.04`.  Identical to the CPU image except
  PPC is compiled with `make gpu arch=${SM_ARCH}` (default SM 89, Ada
  Lovelace); the CPU PPC fallback is also built.  Override the SM architecture
  at build time with `--build-arg SM_ARCH=80` (A100) etc.

- **`container/build_proposal_tables.py`** — shared script (promoted from
  `container/new_kernel/`) that triggers PROPOSAL table generation at
  image-build time so the first simulation run inside the container is instant.

- **`container/README.md`** — pull / run / Singularity conversion
  instructions, local build commands, SM architecture reference table, and a
  guide to publishing new releases via GitHub Actions.

- **`scripts/docker_test.sh`** — local offline test script.  Builds the image
  and validates it before pushing: smoke tests (`tests/test_smoke.py`) then
  the full fast unit suite.  Flags: `--gpu` (test GPU image), `--no-build`
  (skip build step), `--tag TAG` (custom image tag), `--e2e` (add the
  100-event physics regression test, ~8 min extra).  Exit codes 1–4 map to
  build failure, smoke failure, unit-test failure, and e2e failure
  respectively.

- **`.github/workflows/docker-publish.yml`** — manual `workflow_dispatch`
  GitHub Actions workflow that builds and pushes images to GHCR
  (`ghcr.io/harvard-neutrino/prometheus`).  Inputs: `version` (tag, e.g.
  `v2.0`), `variant` (`cpu` / `gpu` / `both`), `sm_arch` (CUDA SM
  architecture, default `89`).  Produces versioned and `:latest` tags for
  both variants.

#### CI — notebook output check

- **`.github/workflows/ci.yml`** — added `notebook-output-check` job that
  runs before the test job on every push/PR.  Installs `nbstripout` and fails
  if any `.ipynb` file in the repository contains stored outputs.

#### Git hooks

- **`scripts/install_hooks.sh`** — installs a `pre-push` git hook that
  automatically strips Jupyter notebook outputs via `nbstripout` before each
  push.  If any notebook is found with outputs, the hook strips them, commits
  the clean versions, and asks the developer to re-push.  Run once after
  cloning: `bash scripts/install_hooks.sh`.

#### Examples

- **`examples/03_docker_water.py`** — runs the standard water-case simulation
  inside the `prometheus:cpu` Docker image (or any image specified via
  `--image`).  Accepts CLI arguments for all key simulation parameters:
  `--nevents`, `--geo`, `--seed`, `--ranged`, `--min-energy`, `--max-energy`.
  Output files (parquet + LeptonInjector HDF5) are written to a host
  directory (default `./output`) via a Docker volume mount (`--output-dir`).

- **`examples/04_event_view.py`** — 3-D matplotlib event visualisation.
  Loads a Prometheus parquet output file and renders a 3-D scatter plot of
  all OMs.  By default shows the brightest event (most photon hits).
  Hit OMs are drawn as colored spheres: color encodes mean photon arrival
  time (black → purple → orange = early → late) and sphere size is
  proportional to √(photon count).  Unhit OMs appear as small black dots.
  Background color is automatically set to dark water-blue or light ice-blue
  based on the geo file medium.  Flags: `--geo`, `--event`, `--out`,
  `--show`, `--dpi`.

### Changed

- **`examples/`** — all pre-existing example scripts and notebooks moved to
  `examples/legacy/` to separate the validated v2 examples from the older
  exploratory ones.

### Removed

#### macOS support

macOS is no longer supported in the native installer.  The primary reason is
that the PROPOSAL build system downloads and compiles Boost 1.85 from source
via Conan (≈5 GB of temporary storage), which routinely causes disk-space
failures on macOS developer machines.  macOS users should use the Docker image
instead.

- **`install.sh`** — added a Darwin guard at the top that exits immediately
  with a clear message pointing to the Docker image.

- **`scripts/setup_env.sh`** — removed `Darwin-x86_64` and `Darwin-arm64`
  cases from platform detection; the unsupported-platform error message now
  mentions Docker.

- **`scripts/activate.sh`** — removed "zsh on macOS" comment (functionality
  unchanged).

- **`scripts/install_leptoninjector_legacy.sh`** — removed
  `|| sysctl -n hw.logicalcpu` fallback from both `nproc` calls (Linux only).

- **`scripts/install_ppc.sh`** — removed the Darwin early-exit block (macOS
  is now blocked at the `install.sh` level).

- **`INSTALL_NOTES.md`** — rewritten: macOS row in the platform table updated
  to "Not supported — use Docker image"; macOS-specific notes section deleted.

- **`README.md`** — "Install from Source" renamed to "Install from Source
  (Linux only)" with a prominent `IMPORTANT` callout; Docker image pointer
  added for macOS users.
