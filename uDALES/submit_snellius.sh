#!/bin/bash

#SBATCH --job-name="les_002" 		# Name of the job for checking
#SBATCH --time=48:00:00		        # Wall clock time requested hh:mm:ss
#SBATCH --partition=genoa		# Which partition?
#SBATCH --ntasks=384  	                # Number of CPU's
#SBATCH --cpus-per-task=1		# CPUs per task
#SBATCH --nodes=2			# Number of nodes


# Define uDALES
export uDALES_HOME="/home/apatil1/u-dales"
export my_exp_num="002"
# LOAD MODULE
echo "**LOADING MODULES**"
module load 2025 OpenMPI/5.0.7-GCC-14.2.0 CMake/3.31.3-GCCcore-14.2.0 FFTW/3.3.10-GCC-14.2.0 netCDF-Fortran/4.6.2-gompi-2025a netCDF/4.9.3-gompi-2025a
echo "**RUNNING JOB NOW**"
# Copy Executables -- Step 1
cp ${uDALES_HOME}/build/release/u-dales .
cp namoptions.${my_exp_num} namoptions

srun u-dales

echo "**FIN**"
