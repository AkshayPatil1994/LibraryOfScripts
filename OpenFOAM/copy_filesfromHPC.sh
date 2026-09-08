#!/bin/bash
# ---
# purpose: rsyncs simulation result folders from a remote HPC (via ssh alias) to local fields_<angle> dirs.
# usage: edit startAngle/endAngle/location inline.
# tags: utility
# ---

# User input parameters
startAngle=50			# Starting angle of the simulations
interval=1			# Interval between each case
endAngle=68			# ending angle of the simulations
endTime=1200			# End time of the simulation
# Location from where to copy files
location='path_on_the_server'
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
echo "** This script will copy $numSim simulation results  **"
echo "***- - - - - - - - - - - - - - - - - - - - ***"
# Create the folders before copying
for ((folderName=${startAngle};folderName<=${endAngle};folderName+=${interval})); do
    echo "-- Copying files for case $folderName --"
    file2copy="dblue:$location/$folderName/$endTime"        # Change dblue to the name of the server config on your ssh/config
    # Now copy the files
    rsync -r $file2copy "fields_$folderName/"
    echo "Done with $folderName ....."
    echo "---------------------------"
done
