#!/bin/bash

numberOfJobs=16			# Total number of jobs to run i.e., siminterval*10 is the final end iterations
startValue=1    	        # Starting the iteration for job1 with this value of end iterations
siminterval=80000		# This is the number of iterations each simulation runs
dt_interval=2000		# This is the total interval between each submission
location='inputFiles'		# Name of the folder where all input files will be stashed
casename='Re500_' 		# Prefix for the name of the job submission
orgslurmfilename='submit.sh'	# Name of the base slurm file used as template
ic_synthetic="yes"		# Is the starting initial condition true
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# 	DO NOT CHANGE THINGS BELOW UNLESS ABSOLUTELY SURE	      #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# Check if the folder exists
if [ ! -d "$location" ]; then
  # Folder does not exist, so create it
  mkdir -p "$location"
  echo "Folder created: $location"
else
  # Folder exists
  echo "Folder already exists: $location"
fi
# Set the endValue for the first job
myEndValue=$((siminterval))
# Set the value of restart time
restartTime=0
# Now loop over the number of jobs and submit them one by one after the basic edits
for ((nj=1;nj<=${numberOfJobs};nj++)); do
        # If startValue if equal to siminterval then change restart type to false
	sed -i "s/^\s*ifirst\s*=.*/ifirst= $startValue/" retau.input
	sed -i "s/^\s*ilast\s*=.*/ilast= $myEndValue/" retau.input
	# Change the restart mode for lpt file
	if [ "$startValue" -eq "1" ]; then
        	sed -i "s/^\s*RestartFlag\s*=\s*[A-Za-z]/RestartFlag = F/" lpt.input
		sed -i "s/^\s*RestartFlag\s*=\s*[A-Za-z]/RestartFlag = F/" retau.input
	else
        	sed -i "s/^\s*RestartFlag\s*=\s*[A-Za-z]/RestartFlag = T/" lpt.input
 		sed -i "s/^\s*RestartFlag\s*=\s*[A-Za-z]/RestartFlag = T/" retau.input
	fi
	# IC is synthetic then force change restart flag to T
	if [ "$ic_synthetic" == "yes" ]; then
		sed -i "s/^\s*RestartFlag = [A-Z]/RestartFlag = T/" retau.input
	fi
	# Change the restart time
	sed -i "s/^\s*myRestartTime\s*=.*/myRestartTime= $restartTime/" retau.input
	# Setup the dns.in_jobnumber input file
	inputfilename="retau.input_job${nj}"
	inputfilename_lpt="lpt.input_job${nj}"
 	# Setup the slurm submission file
	slurmsubfile="slurm_job_${nj}.sh"
	# Copy the file to requisite location
	cp retau.input "${location}/${inputfilename}"
	cp lpt.input "${location}/${inputfilename_lpt}"
	# Now make a copy of the slurm file and replace EDIT-ME with the right file
	finalinputfilename="${location}/${inputfilename}"
	finalinputfilename_lpt="${location}/${inputfilename_lpt}"
	echo $finalinputfilename $finalinputfilename_lpt
	# Change the name of the job
	sed_command="s/--job-name=\"[^\"]*\"/--job-name=\"${casename}${nj}\"/"
	sed -i "$sed_command" "$orgslurmfilename"
	#sed "s|LPT-NAME|$finalinputfilename_lpt|" "$orgslurmfilename" > "$slurmsubfile"
	#sed "s|EDIT-ME|$finalinputfilename|" "$orgslurmfilename" > "$slurmsubfile"
	sed -e "s|LPT-NAME|$finalinputfilename_lpt|" -e "s|EDIT-ME|$finalinputfilename|" "$orgslurmfilename" > "$slurmsubfile"
	# Now edit the LOGFILENAME to be consistent with the run logs
	mynewlogfile="run_${nj}.log"
	sed -i "s|LOGFILENAME|$mynewlogfile|" "$slurmsubfile"
	# Now submit the jobs with appropriate dependency
	#if [ "$nj" -eq 1 ]; then
	#	oldjobid=$(sbatch "$slurmsubfile" | cut -f 4 -d' ')
        #else
	#	oldjobid=$(sbatch --dependency=afterok:"${oldjobid}" "$slurmsubfile" | cut -f 4 -d' ')
        #fi
	# Increment the start value
	startValue=$((startValue + siminterval))
	# Increment the value by the interval
	myEndValue=$((myEndValue + siminterval))
	# Increment the restart value
	restartTime=$((restartTime + dt_interval))
done
# Print helpful message
echo "Make sure you change the value of p_rows and p_cols in the base file....."
