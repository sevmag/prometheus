#!/bin/bash
#SBATCH -c 4       # Number of cores (-c)
#SBATCH -t 0-28:00     # Runtime in D-HH:MM, minimum of 10 minutes
#SBATCH -p arguelles_delgado_gpu  # Partition to submit to
#SBATCH --gres=gpu:nvidia_a100_1g.10gb:1
#SBATCH --mem=5000      # Memory pool for all cores (see also --mem-per-cpu)
#SBATCH -o /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/logging/myoutput_%j.out # File to which STDOUT will be written, %j inserts jobid
#SBATCH -e /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/logging/myerrors_%j.err # File to which STDERR will be written, %j inserts jobid
#SBATCH --array=1001-1010 

source /n/holylfs05/LABS/arguelles_delgado_lab/Lab/common_software/setup_rocky.sh
export PYTHONPATH=/n/home03/pzhelnin/.local/lib/python3.7/site-packages/:$PYTHONPATH
module load cuda/9.1.85-fasrc01

save_dir="/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/output/"

python fasrc_example_ppc.py -n 5000 -s ${SLURM_ARRAY_TASK_ID} --final_1 "MuMinus" --output_prefix "$save_dir"
