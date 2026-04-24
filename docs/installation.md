# Installation

This page describes the supported installation paths for Prometheus: using the
included installer (recommended), or using container images (recommended for
macOS, Windows, and cluster usage).

Requirements
------------

- Python 3.11 or higher.
- A POSIX-compatible shell for the installer (Linux/macOS). For macOS and
    Windows native installs we recommend using the container instead (see
    "Container images").

Quick start
-----------

Clone the repository and run the installer (recommended first step):

```bash
git clone https://github.com/Harvard-Neutrino/prometheus.git
cd prometheus

# Water-only (recommended first install):
bash install.sh

# Water + ice (requires a C++ toolchain and Linux):
bash install.sh --with-ppc
```

What the installer does
-----------------------

1. Download a suitable `micromamba` binary for your OS and architecture.
2. Create a self-contained conda environment at `.prometheus_env/` using
     `environment.yml`.
3. Install optional native dependencies (PROPOSAL, LeptonInjector, PPC) as
     requested. Use `--with-ppc` to build the ice photon-propagator (Linux only).
4. Install the `prometheus` package in editable mode and fetch `fennel-seed`
     as needed.

Activate the environment
------------------------

After the installer finishes, open a new shell and activate the environment:

```bash
source scripts/activate.sh .prometheus_env
```

Use the same command in each new terminal session, or add it to your shell
profile (`~/.bashrc` / `~/.zshrc`) if you prefer.

Running examples
----------------

Try the small example scripts to verify your installation:

```bash
python examples/01_basic_water.py    # water-mode example (JAX)
python examples/02_basic_ice.py      # ice-mode example (PPC, Linux only)
```

Supported platforms and notes
-----------------------------

| Platform | Status |
|---|---|
| Linux x86-64 | Fully supported |
| Linux aarch64 | Supported (LI build untested) |
| macOS | Not supported natively — use the container image |
| Windows (native) | Not supported natively — use the container image |
| Windows WSL2 | Same as Linux x86-64 |

The installer was developed and tested on Ubuntu 22.04 / 24.04. `curl` is
required for the installer to download `micromamba`.

Known limitations
-----------------

- macOS / Windows: build failures for PROPOSAL and LeptonInjector; use the
    container images instead.
- PPC (ice photon-propagator) requires `--with-ppc` during install and is only
    supported on Linux.
- GENIE and some analysis utilities require optional Python packages (e.g.
    `uproot`, `pandas`). See `refactor.md` for more details.

Container images (Docker / Singularity)
--------------------------------------

We publish prebuilt images to GitHub Container Registry (GHCR):

| Tag pattern | Contents |
|---|---|
| `ghcr.io/harvard-neutrino/prometheus:VERSION` | CPU-only build |
| `ghcr.io/harvard-neutrino/prometheus:VERSION-gpu` | CUDA GPU build |
| `ghcr.io/harvard-neutrino/prometheus:latest` | Latest CPU release |
| `ghcr.io/harvard-neutrino/prometheus:latest-gpu` | Latest GPU release |

Pull the image:

```bash
# CPU image
docker pull ghcr.io/harvard-neutrino/prometheus:latest

# GPU image
docker pull ghcr.io/harvard-neutrino/prometheus:latest-gpu
```

Run an interactive shell in the CPU image:

```bash
docker run --rm -it ghcr.io/harvard-neutrino/prometheus:latest
```

Run a script and mount the `output/` directory:

```bash
docker run --rm -v "$PWD/output:/output" ghcr.io/harvard-neutrino/prometheus:latest \
        python /opt/prometheus/examples/01_basic_water.py
```

GPU support
-----------

GPU images require the NVIDIA Container Toolkit on the host. Example:

```bash
docker run --rm -it --gpus all ghcr.io/harvard-neutrino/prometheus:latest-gpu
```

Converting to Singularity/Apptainer
----------------------------------

You can convert GHCR Docker images to Singularity images for HPC clusters:

```bash
singularity pull docker://ghcr.io/harvard-neutrino/prometheus:latest
# Produces: prometheus_latest.sif
```

Then run on the cluster:

```bash
singularity exec prometheus_latest.sif python /opt/prometheus/examples/01_basic_water.py
```

Building images locally
-----------------------

From the repository root you can build images locally:

```bash
# CPU image
docker build -f container/Dockerfile -t prometheus:cpu .

# GPU image
docker build -f container/Dockerfile.gpu -t prometheus:gpu .

# GPU image with specific SM arch
docker build -f container/Dockerfile.gpu --build-arg SM_ARCH=80 -t prometheus:gpu-sm80 .
```

Testing images locally
----------------------

Use the provided test script to build and validate images:

```bash
# Build + smoke tests + fast unit tests (CPU)
bash scripts/docker_test.sh

# GPU image
bash scripts/docker_test.sh --gpu

# Include the 100-event physics regression test (longer)
bash scripts/docker_test.sh --e2e

# Test a pre-built image without rebuilding
bash scripts/docker_test.sh --no-build --tag prometheus:cpu
```

Publishing releases
-------------------

Images are published via GitHub Actions (manual dispatch). See the Actions
workflow for fields and dispatch options.

Troubleshooting and getting help
--------------------------------

- If the installer fails on PROPOSAL or LeptonInjector builds, prefer the
    container images for macOS/Windows or retry the installer on a Linux host.
- If you see missing optional Python packages for analysis utilities, install
    them with `pip install uproot pandas` or check `refactor.md` for details.

If you still need help, open a discussion on GitHub: https://github.com/Harvard-Neutrino/prometheus/discussions

