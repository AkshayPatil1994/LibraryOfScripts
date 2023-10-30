#!/bin/bash

# Source the functions.sh file
source functions.sh
# Name of all the turbulence closures
turbClosure=("kOmegaSST" "kEpsilon")
retauarray=("200" "400" "600" "800" "1000" "1500" "2000" "2500" "3000" "5000")
# Query the size of the arrays
lenTurb=${#turbClosure[@]}
lenRetau=${#retauarray[@]}
echo "The script loops over $((lenTurb)) closure models and $((lenRetau)) cases..."
# Make sure that residuals folder exists
if [ -d "residuals" ]; then
	echo "Residuals folder already exists....."
else
	echo "Generating residuals folder....."
	mkdir residuals
fi
# Loop over all the turbulence closures and Retau and grab the residuals
simStartTime=`date +%s`
for ((i=0; i<${lenTurb};i++)); do
	for ((j=0;j<${lenRetau};j++)); do
		logfile="logs/${turbClosure[$((i))]}_run_${retauarray[$((j))]}.log"
		outfileprefix="${retauarray[$((j))]}${turbClosure[$((i))]}"
		getlogdata $logfile $outfileprefix
		echo "Done with file -- $logfile, $i, $j"
	done
done
simEndTime=`date +%s`
simTotalTime=$((simEndTime-simStartTime))
echo "Script finished in $simTotalTime seconds..."
echo "-------------------------------------------"
