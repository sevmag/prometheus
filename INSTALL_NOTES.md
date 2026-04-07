# Installation Notes

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/Harvard-Neutrino/prometheus.git
cd prometheus
```

### 2. Run the installer

**Water-mode only (recommended first install):**

```bash
bash install.sh
```

**Water + ice mode (requires a C++ compiler):**

```bash
bash install.sh --with-ppc
```

The installer will:
1. Download the correct `micromamba` binary for your OS and architecture.
2. Create a self-contained conda environment at `.prometheus_env/` using `environment.yml`.
3. Install PROPOSAL (lepton energy-loss library) via pip.
4. Build and install LeptonInjector from the vendored source in `resources/LeptonInjector/`.
5. *(with `--with-ppc`)* Compile the PPC ice-photon propagator from `resources/PPC_executables/PPC/`.
6. Install the `prometheus` package itself in editable mode, plus `fennel-seed` from `resources/fennel/`.

Total time: ~10–20 minutes on first install (LI CMake build dominates).

### 3. Activate the environment

Run this in every new terminal before using Prometheus:

```bash
source scripts/activate.sh .prometheus_env
```

To avoid typing this every session, add it to your shell profile (`~/.bashrc` or `~/.zshrc`).

### 4. Run the examples

**Example 01 — water simulation (olympus/JAX, P-ONE geometry):**

```bash
python examples/01_basic_water.py
```

Runs one neutrino event through the water-Cherenkov simulation. Output is written to `output/` in the current directory (created automatically). Expected output: several hundred photon hits on the detector modules.

**Example 02 — ice simulation (PPC, IceCube geometry):**

```bash
python examples/02_basic_ice.py
```

Requires `--with-ppc` at install time and Linux (PPC is not available on macOS). Output is written to `output/` in the current directory.

---

## Supported platforms

| Platform | Status |
|---|---|
| Linux x86-64 | Fully supported |
| Linux aarch64 | Supported (LI build untested) |
| macOS | **Not supported** — use the Docker image |
| Windows (native) | Not supported — use the Docker image |
| Windows WSL2 | Same as Linux x86-64 |

macOS support was dropped because PROPOSAL's Conan/Boost build and
LeptonInjector's CMake build both fail consistently on macOS.
Docker is the recommended path for macOS and Windows users.

---

## Linux notes

The installer was developed and tested on Ubuntu 22.04 / 24.04 (x86-64). It should
work on any modern Debian/Ubuntu or RHEL-based distribution. `curl` must be
available (`apt install curl` / `dnf install curl`).

---

## Known limitations

| Issue | Workaround |
|---|---|
| macOS / Windows not supported natively | Use the Docker image |
| PPC not available without `--with-ppc` | Pass `--with-ppc` at install time (Linux only) |
| GENIE loading requires optional deps | `pip install uproot pandas` or see Phase 13 of refactor.md |
| Intel Arc GPU not accessible in WSL2 | Requires `intel-compute-runtime` inside WSL2 and a recent Windows Intel Graphics driver |
