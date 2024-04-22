#!/bin/bash
simEndTime=3000 # Simulation end time
startAngle=5   # Starting angle of the simulation
endAngle=355    # Ending value of the angle
interval=5     # Interval/increment between each angle
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
#       Do not touch beyond this line unless you are absolutely sure of what              #
#       you are doing                                                                     #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# Source OF environment
#source /home/akshay/OpenFOAM/OpenFOAM-7/etc/bashrc &> /dev/null		# for Noether
source /opt/openfoam7/etc/bashrc &> /dev/null				# for Foote
# Setting up the array for all the angles used in this simulation
simangles=()
for ((i=${startAngle};i<=${endAngle};i+=${interval})); do
        simangles+=($i)
done
# Get the size of the simangles array
numSim=${#simangles[@]}
echo "*** This script will run $numSim post-processing rounds ***"
echo "Starting Angle: ${simangles[0]} | Ending Angle: ${simangles[$((numSim-1))]}"
# Starting the analysis loop
for ((i=0;i<$numSim;i++)); do
	st=`date +%s`
	# Setup the filename
#	filename="results/fields_${simangles[$i]}/$simEndTime"
	filename="results/fields_${simangles[$i]}/*"
	echo "** Running case $((i+1)) of $numSim | file: $filename **"
	# Copy the right file for current analysis
	rsync -rhP $filename ${simEndTime}
	# Now run the postProcessing tools
	logfile="logs/postprocess_${simangles[$i]}.log"
	simpleFoam -postProcess -latestTime > $logfile
	# Move the files to the right location
	postfile="results/postProcessing_${simangles[$i]}"
	mv postProcessing $postfile
	et=`date +%s`
	# Completion message
	tt=$(echo "scale=4; $et - $st" | bc)
        hrconv=3600.0
        tt_hour=$(echo "scale=4; $tt/$hrconv" | bc)
        echo "Total time for case $((i+1)) is $tt seconds .or. $tt_hour hours"
	echo "- - - -"
done
