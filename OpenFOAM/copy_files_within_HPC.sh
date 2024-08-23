#!/bin/bash

startindex=1
interval=1
endindex=2
casetype="1storder"
fileindex="1200"
location="group_storage_location"

# Copy files
for ((i=${startindex};i<=${endindex};i+=${interval})); do
	echo "*** Copying files for ${i}/${fileindex} ***"
	# Make a directory for the right filelocation
	if [ -d "${location}/${i}" ]; then
		echo "Directory exists, skipping creation..."
	else
		mkdir "${location}/${i}"
	fi
	# Copy the fields to the location
	rsync -rhP "${i}/${fileindex}" "${location}/${i}/"
	# Copy the logfile for the given run
	rsync -rhP "${i}/run.log" "${location}/${i}/run_${casetype}.log"
	echo "-----------------------------------"
done
