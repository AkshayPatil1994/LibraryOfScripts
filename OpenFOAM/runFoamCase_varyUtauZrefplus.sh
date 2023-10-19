#!/bin/bash

# User input data for the simulations
nprocs=24
totalIterations=2
# Specify the values of utau and zplusref to be used in the simulations
utauarray=("2e-3" "4e-3" "6e-3" "8e-3" "1e-2" "1.5e-2" "2e-2" "2.5e-2" "3e-2" "5e-2")
zplusref=("200" "400" "600" "800" "1000" "1500" "2000" "2500" "3000" "5000")
# Text color variables
RED='\033[0;31m'
GREEN='\033[0;32m'
RESET='\033[0m' # Reset text color to default
# Query the size of the arrays
lengthz=${#zplusref[@]}
lengthu=${#utauarray[@]}
# Ensure that the arrays are of same size
if [ ${lengthz} -eq ${lengthu} ]; then
    echo "--------------------------------------------------------"
    echo " This script runs $lengthz cases using simpleFoam"
    echo -e " Number of processors: ${RED} $nprocs ${RESET}"
    echo -e " Total Iterations per simulation: ${RED} $totalIterations ${RESET}"
    echo "--------------------------------------------------------"
    echo "		*	*	*"
else
    echo "The size of the utauarray is not equal to zplusref!....."
    echo "The script has terminated, please fix the error above..."
    exit 1
fi
# Measure start time of the script
startTime=`date +%s`
# Loop over all the array input to run the cases one by one
for ((i=0; i<${#zplusref[@]}; i++)); do
    # Query simulation start time
    simStartTime=`date +%s`
    echo "--------------------------------------------------------"
    echo -e "Now running case ${RED} $((i+1)) ${RESET} with  ${RED} Rek = ${zplusref[$i]} ${RESET}"
    # Construct the sed command dynamically
    sed_command="s/\\(ustar[[:space:]]*\\)[0-9.]*e-[0-9]*/\\1${utauarray[$i]}/"
    # Use eval to execute the sed command
    eval "sed -i \"$sed_command\" 0/include/ABLConditions"
    # Now replace the value of zplusref using the same logic
    sed_command="s/zplusref[[:space:]]*[0-9]*;/zplusref		${zplusref[$i]};/"
    eval "sed -i \"$sed_command\" 0/include/ABLConditions"
    echo "I/O check that the right values are changed in 0/include/ABLConditions..."
    cat 0/include/ABLConditions | grep "Friction velocity"
    cat 0/include/ABLConditions | grep "Reference wall units"
    # Set the name of the logfile to log the run I/O
    logfile="logs/run_${zplusref[$i]}.log"
    echo "Simulation I/O logged to file $logfile"
    # Decompose the case again
    decomposePar -force 2>&1 logs/decomposePar.log
    # Run the case
    mpirun -np $nprocs simpleFoam -parallel 2>&1 "$logfile"
    # Reconstruct the simulation
    reconstructPar -latestTime 2>&1 logs/reconstruct.log
    # Move the results to a results folder
    outputFolderName="results/SF${zplusref[$i]}"
    echo -e "Results for this case now moved to -- ${RED} $outputFolderName ${RESET}"
    mv $totalIterations $outputFolderName
    # Query simulation end time
    simEndTime=`date +%s`
    simTotalTime=$((simEndTime-simStartTime))
    echo "Case $((i+1)) took $simTotalTime seconds to finish............"
done
# Measure start time of the script
endTime=`date +%s`
runtime=$((endTime-startTime))
echo "--------------------------------------------------------"
echo "$lengthz cases completed in $runtime seconds............"
echo "			* * *"
echo "--------------------------------------------------------"
