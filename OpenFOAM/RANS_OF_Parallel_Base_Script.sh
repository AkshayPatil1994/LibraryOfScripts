#!/bin/bash

#SBATCH --job-name="NameOfJob"		# Name of the job for checking
#SBATCH --time=04:30:00			      # Wall clock time requested
#SBATCH --partition=compute-p2		# Which partition?
#SBATCH --account=research-abe-ur	# Account to charge
#SBATCH --tasks=64			          # Number of tasks
#SBATCH --cpus-per-task=1		      # Number of cpu per task
#SBATCH --mem=100G			          # Ask for 100GiB of memory

### Run all the cases ###
nProcs=64		# Number of processors used for simpleFoam
verbose=1		# Would you like to print extra information?
simEndTime=1200		# Simulation end time
casetype="1st_order"	# Type of simulation
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
#	Do not touch beyond this line unless you are absolutely sure of what		  #
#       you are doing									  #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# Load the right modules
module load DefaultModules slurm/current 2024rc1 openmpi/4.1.6
# Source OpenFOAM
source /home/apatil5/OpenFOAM-7/etc/bashrc
# Source the fix for UCX library
export UCX_PROTO_ENABLE=n
# Copy system/fvSchemes
cp system/fvSchemes_1storder system/fvSchemes
# First change the number number of processors in decomposeParDict
sed_command="s/numberOfSubdomains [0-9]\+;/numberOfSubdomains ${nProcs};/g"
eval "sed -i \"$sed_command\" system/decomposeParDict"
# Second change the end time in system/controlDict to the right value
sed_command="s/\(endTime[[:space:]]*\)[0-9]\{1,\};/\1${simEndTime};/"
eval "sed -i \"$sed_command\" system/controlDict"
sed_command="s/\(writeInterval[[:space:]]*\)[0-9]\{1,\};/\1${simEndTime};/"
eval "sed -i \"$sed_command\" system/controlDict"
# Verbose print
if [ ${verbose} == 1 ]; then
	echo "* Number of processors changed *"
	cat system/decomposeParDict | grep "numberOfSubdomains"
	echo "* Simulation endTime and writeInterval changed *"
	cat system/controlDict | grep "endTime"
	cat system/controlDict | grep "writeInterval"
fi
##################################################################################
#Step 1: Decompose the case
echo "Step 1: Decomposing case"
srun -n 1 decomposePar -force > decomposePar.log 2>&1
#Step 2: Run the case
echo "Step 2: Running case"
mpirun -np $nProcs simpleFoam -parallel > run.log 2>&1
#Step 3: Reconstruct the case
echo "Step 3: Reconstructing case"
srun -n 1 reconstructPar -latestTime > reconstruct.log 2>&1
#Step 4: Remove decomposed processor folders
rm -rf processor*
# END THE SCRIPT
echo "*** FIN ***"
