#!/bin/bash
simEndTime=3000 # Simulation end time
startAngle=5   # Starting angle of the simulation
endAngle=360    # Ending value of the angle
interval=5     # Interval/increment between each angle
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
#       Do not touch beyond this line unless you are absolutely sure of what              #
#       you are doing                                                                     #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
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
counter=${startAngle}
for ((i=0;i<$numSim;i++)); do
	# Setup the filename
	filename1="results/fields_${simangles[$i]}/$simEndTime/U"
	filename2="results/fields_${simangles[$i]}/$simEndTime/k"
	# Copy the right file for current analysis
	rsync -rhP ${filename1} ${filename2} $counter
	# Increment the counter
	counter=$((counter+${interval}))
	# Now run the postProcessing tools
	echo "- - - -"
done
