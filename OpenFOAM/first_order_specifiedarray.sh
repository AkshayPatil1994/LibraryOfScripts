#!/bin/bash

#SBATCH --job-name="lod1p2"		# Name of the job for checking
#SBATCH --time=64:00:00			# Wall clock time requested
#SBATCH --partition=compute-p2		# Which partition?
#SBATCH --account=<research account name> # Account to charge
#SBATCH --nodes=1			# Number of nodes
#SBATCH --tasks=64			# Number of tasks
#SBATCH --cpus-per-task=1		# Number of cpu per task
#SBATCH --exclusive			# Get the exclusive node
#SBATCH --mem=0				# Get all the memory

# Load the right modules
module load 2023r1 openmpi
# Source the openfoam environment
source /home/apatil5/OpenFOAM-7/etc/bashrc
### Run all the cases ###
nProcs=64		# Number of processors used for simpleFoam
verbose=1		# Would you like to print extra information?
simEndTime=1200		# Simulation end time
casetype="1st_order"	# Type of simulation
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
#	Do not touch beyond this line unless you are absolutely sure of what		  #
#       you are doing									  #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# Copy system/fvSchemes
cp system/fvSchemes_1storder system/fvSchemes
# Setting up the array for all the angles used in this simulation
simangles=("30" "50" "55" "120" "125" "135" "140" "150" "155")
# Get the size of the simangles array
numSim=${#simangles[@]}
echo "*** This script will run $numSim simulations ***"
echo "Starting Angle: ${simangles[0]} | Ending Angle: ${simangles[$((numSim-1))]}"
echo "All simulation angles: ${simangles[@]}"
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
# Now start the loop to run all the cases
for ((j=0;j<${numSim};j++)); do
	#Step 0: Edit the input files in 0/include/ABLconditions
	st=`date +%s`
	echo "*** Case $((j+1)) of $numSim | angle: ${simangles[$j]} *** "
	sed_command="s/^\(angle[[:space:]]*\)[0-9]*;/\1${simangles[$j]};/"
	eval "sed -i \"$sed_command\" 0/include/ABLConditions"
	cat 0/include/ABLConditions | grep "angle	"
	#Step 1: Decompose the case
	echo "Step 1: Decomposing case - logfile: decompose_${simangles[$j]}.log"
	dlogfile="decompose_${simangles[$j]}.log"
	srun -n 1 decomposePar -force > logs/$dlogfile 2>&1
	#Step 2: Run the case
	echo "Step 2: Running case - logfile: run_${casetype}_${simangles[$j]}.log"
	runlogfile="run_${casetype}_${simangles[$j]}.log"
	mpirun -np $nProcs simpleFoam -parallel > logs/$runlogfile 2>&1
	#Step 3: Reconstruct the case
	echo "Step 3: Reconstructing case - logfile: reconstruct_${simangles[$j]}.log"
	reconstlogfile="reconstruct_${simangles[$j]}.log"
	srun -n 1 reconstructPar -latestTime > logs/$reconstlogfile 2>&1
	#Step 4: Move the results to the right location
	echo "Step 4: Moving results to fields_${simangles[$j]}/"
	outputfile="fields_${simangles[$j]}/"
	mv $simEndTime results/$outputfile
	#Step 5: Log some output and
	et=`date +%s`
	tt=$(echo "scale=4; $et - $st" | bc)
	hrconv=3600.0
	tt_hour=$(echo "scale=4; $tt/$hrconv" | bc)
	echo "Total time for case $((j+1)) is $tt seconds .or. $tt_hour hours"
done
echo "*** FIN ***"
