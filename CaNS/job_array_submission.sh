#!/bin/bash

numberOfJobs=2			# Total number of jobs to run i.e., siminterval*10 is the final end iterations
startValue=120000		# Starting the iteration for job1 with this value of end iterations
siminterval=120000		# This is the number of iterations each simulation runs
location='inputFiles'		# Name of the folder where all input files will be stashed
casename='re500l'		# Prefix for the name of the job submission
orgslurmfilename='Re500ln.sh'	# Name of the base slurm file used as template
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# 	DO NOT CHANGE THINGS BELOW UNLESS ABSOLUTELY SURE	      #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# Setup the value of the end iteration to the one defined by the user
myEndValue=$startValue
# Check if the folder exists
if [ ! -d "$location" ]; then
  # Folder does not exist, so create it
  mkdir -p "$location"
  echo "Folder created: $location"
else
  # Folder exists
  echo "Folder already exists: $location"
fi
# Now loop over the number of jobs and submit them one by one after the basic edits
for ((nj=1;nj<=${numberOfJobs};nj++)); do
        # If startValue if equal to siminterval then change restart type to false
	if [ "$myEndValue" -eq "$siminterval" ]; then
		sed -i "10s/^[^ ]*/F/" dns.in	# If synthetic IC then always restart
	else
		sed -i "10s/^[^ ]*/T/" dns.in
	fi
	# Setup the dns.in_jobnumber input file
	inputfilename="dns.in_job${nj}"
	# Setup the slurm submission file
	slurmsubfile="slurm_job_${nj}.sh"
	# Final inputfilename
	finalinputfilename="${location}/${inputfilename}"
	# Now change the value of the end interval in dns.in and copy it to the new file
	sed -i "8s/^[^ ]*/$myEndValue/" dns.in
	# Copy the file to requisite location
	cp dns.in "${location}/${inputfilename}"
	# Now make a copy of the slurm file and replace EDIT-ME with the right file
	echo $finalinputfilename
	# Change the name of the job
	sed_command="s/--job-name=\"[^\"]*\"/--job-name=\"${casename}${nj}\"/"
	sed -i "$sed_command" "$orgslurmfilename" #org_slurm.sh
	sed "s|EDIT-ME|$finalinputfilename|" "$orgslurmfilename" > "$slurmsubfile"
	# Now edit the LOGFILENAME to be consistent with the run logs
	mynewlogfile="run_${nj}.log"
	sed -i "s|LOGFILENAME|$mynewlogfile|" "$slurmsubfile"
	# Now submit the jobs with appropriate dependency
	if [ "$nj" -eq 1 ]; then
		oldjobid=$(sbatch "$slurmsubfile" | cut -f 4 -d' ')
        else
		oldjobid=$(sbatch --dependency=afterok:"${oldjobid}" "$slurmsubfile" | cut -f 4 -d' ')
        fi
	# Increment the value by the interval
	myEndValue=$((myEndValue + siminterval))
done
