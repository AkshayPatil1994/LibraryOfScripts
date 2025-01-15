#!/bin/bash

ic_synthetic='yes'		# Is the spin-up synthetic? (yes, no)
numberOfJobs=8			# Total number of jobs to run i.e., siminterval*10 is the final end iterations
startValue=50000		# Starting the iteration for job1 with this value of end iterations
siminterval=50000		# This is the number of iterations each simulation runs
location='inputFiles'		# Name of the folder where all input files will be stashed
casename='cy_' 			# Prefix for the name of the job submission
orgslurmfilename='submit.sh'	# Name of the base slurm file used as template
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
		sed -i "10s/^[^ ]*/F/" dns.in
	else
		sed -i "10s/^[^ ]*/T/" dns.in
	fi
	# Force the value to True if IC's are synthetic
	if [ "$ic_synthetic" = "yes" ] && [ "$myEndValue" -eq "$siminterval" ]; then
		echo "Restart type synthetic forced...."
		sed -i "10s/^[^ ]*/T/" dns.in
		# Edit the name submit.sh script to copy fld.bin
		sed -i 's/^ictype="[^"]*"/ictype="synthetic"/' $orgslurmfilename
	fi
	# If ic_synthetic != "yes"
	if [ "$ic_synthetic" != "yes" ]; then
		sed -i 's/^ictype="[^"]*"/ictype="normal"/' $orgslurmfilename
	fi
	# Setup the dns.in_jobnumber input file
	inputfilename="dns.in_job${nj}"
	# Setup the slurm submission file
	slurmsubfile="slurm_job_${nj}.sh"
	# Final inputfilename
	finalinputfilename="${location}/${inputfilename}"
	# Now change the value of the end interval in dns.in and copy it to the new file
	sed -i "8s/^[^ ]*/$myEndValue/" dns.in
	# Edit the simulation number in the submit script
	sed -i "s/simNum=[0-9]\+/simNum=$nj/" submit.sh
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



### Accompanying script
#!/bin/bash

#SBATCH --job-name="cy_8" 		# Name of the job for checking
#SBATCH --time=40:00:00			# Wall clock time requested hh:mm:ss
#SBATCH --partition=genoa		# Which partition?
#SBATCH --mem=250G			# Amount of memory
#SBATCH -n 576    	                # Number of CPU's

# Tag simulation number as a counter
simNum=8
# Tag the initial condition type
ictype="synthetic"
# Number of processors used
nprocs=576
# Name of the case to be run
casename="casename"
# Base path -- Project space (no end / to be included)
basepath="basepath_in_project"
# Target path -- Scratch shared (no end / to be included)
targetpath="/scratch-shared/$USER/$casename"
# Copy the right input file to working directory
cp EDIT-ME dns.in		# CHANGE VALUE HERE
#
# Load the appropriate modules
#
echo "**LOADING MODULES**"
module load 2024 impi/2021.13.0-intel-compilers-2024.2.0
#
# Source all the compilation paths
#
export PATH="/home/apatil1/fftw/bin:$PATH"
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/apatil1/fftw/lib/
#
# Copy the required data from project to scratch
#
echo "**COPYING THE REQUIRED INPUT DATA TO SCRATCH**"
if [ ! -d "$targetpath" ]; then
	echo "Creating non-existing directory on scratch..."
	mkdir -p "$targetpath/data"
fi
# Only needs the restart if any and the sdf files to be copied
if [ "$simNum" != "1" ] || [ "$ictype" == "synthetic" ]; then
	rsync -rhP "${basepath}/data/fld.bin" "$targetpath/data/"
fi
rsync -rhP ${basepath}/data/sdf*.bin "$targetpath/data/"
rsync -rhP "${basepath}/dns.in" "$basepath/cans" "$targetpath/"
#
# Run the case and log data to file from scratch
#
echo "**RUNNING JOB NOW**"
cd "$targetpath/"
mpirun -np $nprocs ./cans > run.log
# Now move the log file to the right location
mv run.log LOGFILENAME
#
# Copy the results back to project space
#
echo "**COPYING RESULTS BACK TO PROJECT**"
rsync -rhP ${targetpath}/data/* "${basepath}/data/"
rsync -rhP ${targetpath}/LOGFILENAME "${basepath}/"
#
# Finalise the job
#
echo "**FIN**"
