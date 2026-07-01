#!/bin/bash -l
# Prometheus simulation array, wired to the 'prometheus' spack env.
# One array task = one seed = one independent output file. Submit with:
#   sbatch examples/submit_prometheus_spack.sbatch
#SBATCH -J prometheus_sim
#SBATCH --partition=test            # swap for a lab partition (e.g. arguelles_delgado) for big arrays
#SBATCH -c 1
#SBATCH --mem=8G
#SBATCH -t 0-02:00:00
#SBATCH --array=1001-1010           # 10 seeds; each task uses SLURM_ARRAY_TASK_ID as the seed
#SBATCH -o /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/logging/sim_%A_%a.out
#SBATCH -e /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/logging/sim_%A_%a.err

# --- environment (spack, not micromamba) ---
source /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/spack/share/spack/setup-env.sh
spack env activate prometheus

PROM_ROOT=/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus
cd "$PROM_ROOT"
export PPC_EXE=$PROM_ROOT/resources/PPC_executables/PPC/ppc
export PPC_TABLES_DIR=$PROM_ROOT/resources/PPC_tables/south_pole

SAVE_DIR=/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/output/
mkdir -p "$SAVE_DIR" $(dirname /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/logging/x)

# --- one simulation per array task ---
python examples/run_prometheus_sim.py \
  -n 5000 \
  -s ${SLURM_ARRAY_TASK_ID} \
  --final_1 MuMinus --final_2 Hadrons \
  --emin 1e3 --emax 1e6 \
  --geo resources/geofiles/demo_ice.geo \
  --storage-prefix "$SAVE_DIR"
