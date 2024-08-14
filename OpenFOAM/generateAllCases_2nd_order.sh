#!/bin/bash
# User input parameters
startAngle=1			# Starting angle of the simulations
interval=1			# Interval between each case
endAngle=2			# Ending angle of the simulations
endTimeResults='1200'			# End time of the 1st order simulations
resultsLocation='/beegfs/projects/refmap/denHaag/lod1p2/results'	# Location of the results 2 copy from
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
echo "** This script will create $numSim simulations  **"
echo "***- - - - - - - - - - - - - - - - - - - - ***"
# Create the folders before copying
iterator=0
for ((folderName=${startAngle};folderName<=${endAngle};folderName+=${interval})); do
    echo "-- Working on $folderName case right now --"
    mkdir $folderName
    sed_command="s/^\(angle[[:space:]]*\)[0-9]*;/\1${simangles[$iterator]};/"
    eval "sed -i \"$sed_command\" orgCase/0/include/ABLConditions"
    cat orgCase/0/include/ABLConditions | grep "// Angle of attack"
    # Change the name of the case in the slurm script
    sed_command="s/--job-name=\"[^\"]*\"/--job-name=\"a${simangles[$iterator]}l1p2\"/"
    sed -i "$sed_command" orgCase/submit_2ndorder.sh
    cat orgCase/submit_2ndorder.sh | grep "job-name"
    # Copy the files from the orgCase
    echo "Copying the required files ...."
    rsync -rh orgCase/{0,system,submit_2ndorder.sh} "${folderName}"/
    echo "Done with copying ...."
    mkdir "${folderName}"/constant
    cp -rs "$(pwd)"/orgCase/constant/* "${folderName}"/constant/
    # Copy results from the results folder
    cp -rs "${resultsLocation}"/"fields_${folderName}"/"${endTimeResults}" "$folderName"/"${endTimeResults}"
    # Submit the job
    cd "${folderName}"
    echo "Submitting job from dir: $(pwd)"
    #sbatch submit_2ndorder.sh
    # Move back up so that the right path can be used to copy and paste things
    cd ..
    echo "Done with $folderName ....."
    echo "---------------------------"
    # Increment the iterator
    iterator=$((iterator+1))
done
