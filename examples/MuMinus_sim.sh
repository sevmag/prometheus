#!/bin/bash
#SBATCH -c 4       # Number of cores (-c)
#SBATCH -t 0-4:00     # Runtime in D-HH:MM, minimum of 10 minutes
#SBATCH -p arguelles_delgado_gpu_a100,arguelles_delgado_gpu_mixed # Partition to submit to
#SBATCH --gres=gpu
#SBATCH --mem=5000     # Memory pool for all cores (see also --mem-per-cpu)
#SBATCH -o /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/logging/output/myoutput_%j.out # File to which STDOUT will be written, %j inserts jobid
#SBATCH -e /n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/logging/error/myerrors_%j.err # File to which STDERR will be written, %j inserts jobid
#SBATCH --array=1-100

#running this is fine. change the absorption and whatever. 

source /n/holylfs05/LABS/arguelles_delgado_lab/Lab/common_software/setup_rocky.sh
# export PYTHONPATH=/n/home03/pzhelnin/.local/lib/python3.7/site-packages/:$PYTHONPATH
module load cuda/9.1.85-fasrc01

save_dir="/n/holylfs05/LABS/arguelles_delgado_lab/Everyone/pzhelnin/prometheus_output/output/090_icemodel/cascades"

#--force_volume

python fasrc_example_ppc.py -n 100 -s ${SLURM_ARRAY_TASK_ID} --emin 1e3 --emax 1e4 --final_1 "NuEBar" --output_prefix "$save_dir" --force_volume
