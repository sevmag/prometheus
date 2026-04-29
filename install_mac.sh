#!/usr/bin/env bash
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
    echo "ERROR: install_mac.sh is for macOS only. Use install.sh on Linux/WSL2." >&2
    exit 1
fi

ENV_DIR="${PWD}/.prometheus_env"

echo "==== Prometheus macOS Installer ===="

WITH_PPC=0
for arg in "$@"; do
  case $arg in
    --with-ppc) WITH_PPC=1 ;;
  esac
done

# Step 1: Require Homebrew
if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew is required. Install it from https://brew.sh then re-run." >&2
    exit 1
fi

# Step 2: Homebrew C++ dependencies
echo "Installing Homebrew dependencies..."
brew install cmake hdf5 boost boost-python3 eigen gsl pkg-config cfitsio

# Step 3: Create venv from Homebrew Python
# Homebrew Python must be used so that boost-python3 (also Homebrew-built)
# shares the same dynamically-linked Python runtime. conda or actions/setup-python
# Python both statically embed their runtime, causing a two-runtime crash on import.
BREW_PYTHON="$(brew --prefix)/bin/python3"
if [ ! -x "$BREW_PYTHON" ]; then
    echo "ERROR: Homebrew Python not found at $BREW_PYTHON." >&2
    echo "Install it with: brew install python3" >&2
    exit 1
fi

echo "Creating Python environment at $ENV_DIR..."
"$BREW_PYTHON" -m venv "$ENV_DIR"
source "$ENV_DIR/bin/activate"
pip install --upgrade pip
pip install numpy scipy matplotlib cython pybind11

# Step 4: Install PROPOSAL
bash scripts/install_proposal.sh

# Step 5: Build photospline + LeptonInjector
bash scripts/install_leptoninjector_mac.sh "$ENV_DIR"

# Step 6: Install JAX (after LI so numpy ABI is settled)
pip install jax jaxlib

# Step 7: Optional PPC
if [ "$WITH_PPC" -eq 1 ]; then
    bash scripts/install_ppc.sh
fi

# Step 8: Verify
bash scripts/check_install.sh

# Step 9: Post-install (editable prometheus + fennel)
bash scripts/fixes.sh "$ENV_DIR"

echo ""
echo "==== INSTALL COMPLETE ===="
echo "Activate with:"
echo "  source scripts/activate.sh $ENV_DIR"
