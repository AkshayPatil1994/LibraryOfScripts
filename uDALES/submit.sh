#!/bin/bash

#SBATCH --job-name="les_002"            # Name of the job for checking
#SBATCH --time=00:30:00                 # Wall clock time requested hh:mm:ss
#SBATCH --partition=compute-p2          # Which partition?
#SBATCH --account=research-abe-ur       # Account to charge
#SBATCH --mem-per-cpu=3600MB             # Amount of memory per CPU
#SBATCH --cpus-per-task=1               # Number of CPUs per task
#SBATCH -n 32                           # Number of CPUs

# DEFINE SOME USER SPECIFIC DATA
export my_exp_num="002"				# Store the experiment number within the script for internal use
export max_wait_time="3600"			# Number of seconds to sleep for pre-processing to finish (takes roughly 13 minutes to finish)
export uDALES_HOME="${HOME}/uDALES/u-dales"	# Home location for u-dales
export exp_location="$(pwd)"			# Experiment location, typically from where submit.sh is submitted
# Load the appropriate modules
echo "**LOADING MODULES**"
module load DefaultModules
module load 2025
module load openmpi
module load cmake/3.30.5
module load fftw/3.3.10_openmp_True
module load netcdf-c/4.9.2
module load netcdf-fortran/4.6.1
# Matlab required for pre-processing
module load matlab/R2024b
module load gcc/13.3.0
#
# FIRST RUN PREPROCESSING
#
echo "**PRE PROCESSING**"
cd ${uDALES_HOME}				# Run the script from uDALES home location
tools/write_inputs.sh ${exp_location}		# Run the pre-processing script
cd ${exp_location}				# Return back to the experiment location
# Sleep for a specified amount of time until pre-processing is finished
echo "**SLEEPING UNTIL PRE PROCESSING IS FINISHED**"
# Force check that the log file is proprely finished
logcheck=$(grep "Written facetarea.inp.${my_exp_num}" "write_inputs.${my_exp_num}.log")
check_string="Written facetarea.inp.${my_exp_num}"
# Define some preliminary parameters
elapsed=0
sleep_interval=60
# While check for pre-processing setup
while true; do
    # Check if log file contains the string
    if grep -q "$check_string" "write_inputs.${my_exp_num}.log"; then
        echo "Pre-processing finished normally, continue simulation"
        break
    fi

    # If we have waited too long, abort
    if [[ $elapsed -ge $max_wait_time ]]; then
        echo "Pre-processing did not finish within expected time, aborting..."
        exit 1
    fi

    # Sleep and increment elapsed time
    echo "Pre-processing not yet finished, sleeping for ${sleep_interval} seconds..."
    sleep $sleep_interval
    elapsed=$((elapsed + sleep_interval))
done
#
# RUN SIMULATION
#
cp ${uDALES_HOME}/build/release/u-dales .
cp namoptions.${my_exp_num} namoptions
echo "**RUNNING SIMULATION**"
srun --ntasks=8 u-dales
# FINALISE
echo "**FIN**"
