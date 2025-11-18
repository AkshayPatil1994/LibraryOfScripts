#!/bin/bash
angles="1.89"
geo_location="nominal_les_geometry"						# Location where all geometry is stored
geo_prefix="campus"										# Prefix used for the geometry
exp_start_num=2 										# Starting number of the experiment corresponding to 5 degrees
# DEFINE SOME USER SPECIFIC DATA
export max_wait_time="10800"								# Number of seconds to sleep for pre-processing to finish (takes roughly 13 minutes to finish)
export uDALES_HOME="${HOME}/uDALES/u-dales"	# Home location for u-dales
# # # # # # # # #
# CODE - BELOW  #
# # # # # # # # #
# Use internal field seperator to split values using comma seperator
IFS=',' read -r -a angle_array <<< "$angles"
# Loop over all angles and setup the base scripts
for ((i=0;i<${#angle_array[@]};i+=1)); do
	printf -v padded_expnum "%03d" "$((i+${exp_start_num}))"
	echo "Working on setting up ${angle_array[i]} with exp id - $padded_expnum"
	# Check if the experiment directory already exists
	if [ -d "${padded_expnum}" ]; then
		echo "Experiment ${padded_expnum} already exists... Skipping this experiment!"
	else
		# Copy config.sh and namoptions with the correct name
		mkdir ${padded_expnum}
		cp config.sh ${padded_expnum}
		cp namoptions ${padded_expnum}/namoptions.${padded_expnum}
		cp "${geo_location}/${geo_prefix}_${angle_array[i]}.stl" ${padded_expnum}/campus.stl
		#
		# Edit files based on exp_num
		#
		# Change the number of the experiment number inside namptions.${padded_expnum}
		sed -i "s/^\(iexpnr[[:space:]]*=[[:space:]]*\).*/\1${padded_expnum}/" ${padded_expnum}/namoptions.${padded_expnum}	
		#
		# RUN PREPROCESSING
		#
		echo "**PRE PROCESSING**"
		cd ${padded_expnum}				
		exp_location="$(pwd)"			# Fetch the working directory
		cd ${uDALES_HOME}				# Run the script from uDALES home location
		tools/write_inputs.sh ${exp_location}		# Run the pre-processing script
		cd ${exp_location}				# Return back to the experiment location
		# Sleep for a specified amount of time until pre-processing is finished
		echo "**SLEEPING UNTIL PRE PROCESSING IS FINISHED**"
		# Force check that the log file is proprely finished
		check_string="Written facetarea.inp.${padded_expnum}"
		# Define some preliminary parameters
		elapsed=0
		sleep_interval=60
		# While check for pre-processing setup
		while true; do
			# Check if log file contains the string
			if grep -q "$check_string" "write_inputs.${padded_expnum}.log"; then
				echo "Pre-processing finished normally, continue simulation"
				break
			fi

			# If we have waited too long, abort
			if [[ $elapsed -ge $max_wait_time ]]; then
				echo "Pre-processing did not finish within expected time, aborting..."
				exit 1
			fi

			# Sleep and increment elapsed time
			echo -ne "Pre-processing not finished, sleeping for ${sleep_interval} | elapsed: ${elapsed} seconds..\r"
			sleep $sleep_interval
			elapsed=$((elapsed + sleep_interval))
		done		
	fi
	# Move back up one directory
	cd ../
done
