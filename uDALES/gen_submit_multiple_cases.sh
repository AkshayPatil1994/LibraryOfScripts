#!/bin/bash
# Define all angles to be setup for pre-processing seperated by a comma (",")
angles="5,10,15,20"								# Angles to be run (this reads geometry files titled campus_5.stl and so on
driver_exp_num=1								# Driver experiment number
exp_start_num=2									# Starting number of the experiment corresponding to 5 degrees
submit_jobs=1									# 1 - submits jobs, 0 - only generate files without submitting
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
		echo "Experiment ${padded_expnum} already exists..."
	else
		# Copy config.sh and namoptions with the correct name
		mkdir ${padded_expnum}
		cp config.sh ${padded_expnum}
		cp namoptions ${padded_expnum}/namoptions.${padded_expnum}
		cp "coarse_les_geometry/campus_${angle_array[i]}.stl" ${padded_expnum}/campus.stl
		cp submit.sh ${padded_expnum}/
		# Generate soft links to the driver files
		cd ${padded_expnum}/
		cp -rs $(pwd)/../driver_files/* .
		cd ../
		#
		# Edit files based on exp_num
		#
		# Change the number of the experiment number inside namptions.${padded_expnum}
		sed -i "s/^\(iexpnr[[:space:]]*=[[:space:]]*\).*/\1${padded_expnum}/" ${padded_expnum}/namoptions.${padded_expnum}
		# Change the job name in the submit file
		sed -i "s/--job-name=\"[^\"]*\"/--job-name=\"les_${padded_expnum}\"/" ${padded_expnum}/submit.sh
		# Change the experiment number saved within the slurm script
		sed -i "s/export my_exp_num=\"[^\"]*\"/export my_exp_num=\"${padded_expnum}\"/" ${padded_expnum}/submit.sh
	fi

	# Job submission check
	if [ ${submit_jobs} == 1 ]; then
		cd ${padded_expnum}/
		sbatch submit.sh
		cd ..
	fi

done
