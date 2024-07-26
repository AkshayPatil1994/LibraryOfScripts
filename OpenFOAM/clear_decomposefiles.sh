#!/bin/bash
# User input parameters
startAngle=1			# Starting angle of the simulations
interval=1			# Interval between each case
endAngle=14			# ending angle of the simulations
##################################################################################
# DO NOT TOUCH THINGS BELOW UNLESS YOU ARE ABOSLUTELY SURE OF WHAT YOU ARE DOING #
##################################################################################
simangles=()
for ((i=${startAngle};i<=${endAngle};i+=${interval})); do
        simangles+=($i)
done
# Get the size of the simangles array
numSim=${#simangles[@]}
echo "***- - - - - - - - - - - - - - - - - - - - ***"
echo "** This script will clean $numSim simulations  **"
echo "***- - - - - - - - - - - - - - - - - - - - ***"
# Create the folders before copying
for ((i=${startAngle};i<${endAngle};i+=${interval})); do
    folderName=$((i+1))
    echo "-- Clearing processors on $folderName --"
    cd "${folderName}"
    rm -rf processor*
    cd ..
    echo "Done with $folderName ....."
    echo "---------------------------"
done
