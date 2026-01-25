#!/bin/bash

startindex=1
endindex=360
interval=1
logfile="run.log"
logfileextension="1"
#
# Source functions
#
source functions.sh
# Define all angles
echo "***- - - - - - - - - - - - - - - - - - - - ***"
echo "      ** This script gets residuals  **"
echo "***- - - - - - - - - - - - - - - - - - - - ***"
# Create the folders before getting residuals
if [ -d "residuals" ]; then
	echo "Residuals exists..."
else
	mkdir residuals
fi
#
# Get residuals
#
for ((folderName=${startindex};folderName<=${endindex};folderName+=${interval})); do
    logfilename="../${folderName}/${logfile}"
    echo $logfilename ${logfileextension}
    getlogdata ${logfilename} "${logfileextension}"
done
