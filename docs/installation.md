# Installation {#installation}

This page describes how to install **Prometheus** using the built-in installer.

If you prefer a pre-configured environment (recommended for macOS, Windows, or clusters), see:
👉 [Container Installation](containers.md)

---

## Before You Start {#before-you-start}

Prometheus relies on several scientific software components that can be difficult to build manually.
To simplify this, we provide an **automated installer** that sets up everything for you.

!!! tip
  If you are unsure which method to use, we recommend starting with the installer on Linux, or using containers on macOS/Windows.

---

## Requirements {#requirements}

To install Prometheus, you will need:

* **[Python](https://realpython.com/installing-python/)** 3.11 or higher
* A **POSIX-compatible shell** (Linux/macOS)
* `curl` (used by the installer to download dependencies)

!!! note
  Native installation is only fully supported on Linux.
  On macOS and Windows, use containers instead.

---

## Installation Steps {#steps}

### 1. Clone the Repository

```bash
git clone https://github.com/Harvard-Neutrino/prometheus.git
```

```bash
cd prometheus
```

---

### 2. Run the Installer

```bash
bash install.sh
```

This installs the **water-based simulation mode**, which is the recommended starting point.

To enable ice-based simulations:

```bash
bash install.sh --with-ppc
```

!!! note
  The `--with-ppc` option requires a working C++ toolchain and is only supported on Linux.

---

## What Gets Installed {#what-gets-installed}

The installer automatically:

* Creates an isolated environment in `.prometheus_env/`
* Installs all Python dependencies
* Builds required scientific libraries:

  * **[PROPOSAL](https://github.com/tudo-astroparticlephysics/PROPOSAL)** — lepton propagation
  * **[LeptonInjector](https://github.com/icecube/LeptonInjector)** — neutrino interaction generation
* Optionally builds:

  * **[ppc](https://github.com/icecube/ppc)** — photon propagation (ice simulations)

!!! tip
  You do **not** need to install these dependencies manually.

---

## Activate the Environment {#activation}

After installation, activate the environment:

```bash
source scripts/activate.sh .prometheus_env
```

!!! warning
  The environment **must be active** whenever you run Prometheus.
  If it is not activated, commands like `python examples/...` may fail or use the wrong dependencies.

!!! note
  You need to run this command in every new terminal session, unless you add it to your shell profile (`~/.bashrc` or `~/.zshrc`).

---

## Verify the Installation {#verify}

With the environment **activated**, run a simple example:

```bash
python examples/01_basic_water.py
```

If successful, you should see simulation output without errors.

!!! tip
  If you encounter errors, first check that the environment is active before troubleshooting further.

---

## Supported Platforms {#platforms}

| Platform      | Status          |
| ------------- | --------------- |
| Linux x86-64  | Fully supported |
| Linux aarch64 | Supported       |
| macOS         | Use containers  |
| Windows       | Use containers  |
| WSL2          | Supported       |

---

## Troubleshooting {#troubleshooting}

* **Build failures (PROPOSAL / LeptonInjector)**
  → Use containers instead

* **Missing optional Python packages**

```bash
pip install uproot
```

```bash
pip install pandas
```

If problems persist, see: 👉 [Discussions](https://github.com/Harvard-Neutrino/prometheus/discussions)
