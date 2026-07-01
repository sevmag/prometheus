#!/bin/bash
#SBATCH -J prometheus_simulation
#SBATCH -c 1 # Number of cores
#SBATCH -p arguelles_delgado
#SBATCH --mem 10000
#SBATCH -t 0-10:00:00 # Maximum execution time (D-HH:MM:SS)
#SBATCH -o /n/holyscratch01/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/logging/output/prometheus_sim_%A_%a.out # Standard output
#SBATCH -e /n/holyscratch01/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/logging/error/prometheus_sim_%A_%a.err # Standard error

source /n/holylfs05/LABS/arguelles_delgado_lab/Lab/common_software/setup_rocky.sh
export PYTHONPATH=/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus:$PYTHONPATH

python /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus/examples/fasrc_example_ppc.py -n 500 --final_1 "NuEBar" 
#python /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus/examples/fasrc_example_ppc.py -n 500  
