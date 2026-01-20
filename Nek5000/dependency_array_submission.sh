#!/bin/bash

submit_jobs=1					# Set to 1 to submit jobs after creating input files
numberOfJobs=20					# Total number of jobs to run i.e., siminterval*10 is the final end iterations
startValue=83.0 				# starting value of time
siminterval=8.0					# Total time interval for each job
location='inputFiles'				# Name of the folder where all input files will be stashed
casename='tw5-9000'				# Prefix for the name of the job submission
orgslurmfilename='submit.sh'			# Name of the base slurm file used as template
nekcase='duct0'					# Base name for Nek5000 case (used for .f files)
parfile='duct.par'				# Parameter file name
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# 	DO NOT CHANGE THINGS BELOW UNLESS ABSOLUTELY SURE	      #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# SANITY CHECKS
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

# Check if required files exist
if [ ! -f "$orgslurmfilename" ]; then
	echo "ERROR: Base slurm file not found: $orgslurmfilename"
	exit 1
fi

if [ ! -f "$parfile" ]; then
	echo "ERROR: Parameter file not found: $parfile"
	exit 1
fi

# Validate numeric inputs
if ! [[ "$numberOfJobs" =~ ^[0-9]+$ ]] || [ "$numberOfJobs" -lt 1 ]; then
	echo "ERROR: numberOfJobs must be a positive integer (got: $numberOfJobs)"
	exit 1
fi

if ! [[ "$startValue" =~ ^[0-9]+\.?[0-9]*$ ]]; then
	echo "ERROR: startValue must be a number (got: $startValue)"
	exit 1
fi

if ! [[ "$siminterval" =~ ^[0-9]+\.?[0-9]*$ ]] || (( $(echo "$siminterval <= 0" | bc -l) )); then
	echo "ERROR: siminterval must be a positive number (got: $siminterval)"
	exit 1
fi

# Function to find the highest numbered checkpoint file in current directory
find_last_checkpoint() {
	local casename=$1
	local max_num=0

	# Find all checkpoint files matching pattern
	for file in ${casename}.f[0-9]*; do
		if [ -f "$file" ]; then
			# Extract the number from filename
			num=$(echo "$file" | sed "s/${casename}.f0*//")
			if [ ! -z "$num" ] && [ "$num" -gt "$max_num" ]; then
				max_num=$num
			fi
		fi
	done

	echo $max_num
}

# Function to find the highest numbered checkpoint file in fields directory
find_last_checkpoint_in_fields() {
	local casename=$1
	local fields_dir="fields"
	local max_num=0

	if [ ! -d "$fields_dir" ]; then
		echo 0
		return
	fi

	# Find all checkpoint files in fields directory
	for file in ${fields_dir}/${casename}.f[0-9]*; do
		if [ -f "$file" ]; then
			# Extract the number from filename
			filename=$(basename "$file")
			num=$(echo "$filename" | sed "s/${casename}.f0*//")
			if [ ! -z "$num" ] && [ "$num" -gt "$max_num" ]; then
				max_num=$num
			fi
		fi
	done

	echo $max_num
}

# Function to move existing checkpoint files to fields directory
move_checkpoints_to_fields() {
	local casename=$1
	local last_num=$2
	local fields_dir="fields"

	# Create fields directory if it doesn't exist
	if [ ! -d "$fields_dir" ]; then
		mkdir -p "$fields_dir"
		echo "Created fields directory: $fields_dir"
	else
		echo "Fields directory already exists: $fields_dir"
	fi

	if [ $last_num -gt 0 ]; then
		echo "Found existing checkpoint files up to ${casename}.f$(printf "%05d" $last_num)"
		echo "Moving checkpoint files to $fields_dir/..."

		# Move all checkpoint files to fields directory
		local moved_count=0
		for ((i=1; i<=$last_num; i++)); do
			checkpoint_file="${casename}.f$(printf "%05d" $i)"
			if [ -f "$checkpoint_file" ]; then
				mv "$checkpoint_file" "$fields_dir/"
				echo "  Moved $checkpoint_file -> $fields_dir/"
				moved_count=$((moved_count + 1))
			fi
		done

		if [ $moved_count -gt 0 ]; then
			echo "Archived $moved_count checkpoint file(s) in $fields_dir/"
		else
			echo "Warning: Expected $last_num files but none were moved"
		fi
	else
		echo "No existing checkpoint files found. Starting fresh."
	fi
}

# Function to get checkpoint info from slurm output
get_checkpoint_from_slurm() {
	local slurmfile=$1
	local checkpoint_file=""
	local checkpoint_time=""

	# Look for most recent slurm output file
	latest_slurm=$(ls -t slurm-*.out 2>/dev/null | head -1)

	if [ -f "$latest_slurm" ]; then
		echo "Checking $latest_slurm for checkpoint information..."
		# Extract checkpoint information (adjust grep pattern based on actual Nek5000 output)
		checkpoint_line=$(grep -i "checkpoint" "$latest_slurm" | tail -1)

		if [ ! -z "$checkpoint_line" ]; then
			echo "Found checkpoint info: $checkpoint_line"
			# Parse checkpoint file and time from the line
			# This may need adjustment based on actual Nek5000 output format
			checkpoint_file=$(echo "$checkpoint_line" | grep -oP '(?<=file:\s).*?\.f[0-9]+' || echo "")
			checkpoint_time=$(echo "$checkpoint_line" | grep -oP '(?<=time[=:]\s*)[0-9.E+\-]+' || echo "")
		fi
	fi

	echo "$checkpoint_file|$checkpoint_time"
}

# Function to update parameter file with restart information
update_par_file() {
	local parfile=$1
	local restart_file=$2
	local restart_time=$3
	local has_restart=$4

	if [ -f "$parfile" ]; then
		echo "Updating $parfile with restart information..."

		if [ "$has_restart" = "true" ]; then
			# Restart file exists: uncomment/update startFrom line and remove standalone time line
			sed -i "s|^#*startFrom.*|startFrom = $restart_file time=$restart_time|" "$parfile"
			sed -i "/^time = /d" "$parfile"
			echo "  Set startFrom = $restart_file time=$restart_time"
		else
			# No restart file: comment out startFrom and add time = 0.0
			sed -i "s|^startFrom.*|#startFrom = $restart_file|" "$parfile"
			# Remove any existing standalone time line first
			sed -i "/^time = /d" "$parfile"
			# Add time = 0.0 after the commented startFrom line
			sed -i "s|^#startFrom.*|#startFrom = $restart_file\ntime = $restart_time|" "$parfile"
			echo "  Commented out startFrom, set time = $restart_time"
		fi
	else
		echo "Warning: Parameter file $parfile not found!"
	fi
}
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# MOVE EXISTING CHECKPOINT FILES TO FIELDS DIRECTORY
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
echo "========================================"
echo "CHECKPOINT FILE MANAGEMENT"
echo "========================================"

last_checkpoint_num=$(find_last_checkpoint "$nekcase")
move_checkpoints_to_fields "$nekcase" $last_checkpoint_num

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# UPDATE PARAMETER FILE WITH RESTART INFO
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
echo ""
echo "========================================"
echo "UPDATING RESTART INFORMATION"
echo "========================================"

# Try to get checkpoint info from slurm output
checkpoint_info=$(get_checkpoint_from_slurm "$orgslurmfilename")
IFS='|' read -r slurm_checkpoint_file slurm_checkpoint_time <<< "$checkpoint_info"

# Check for checkpoints in fields directory as well
fields_checkpoint_num=$(find_last_checkpoint_in_fields "$nekcase")

# Determine which checkpoint is truly the latest
if [ $fields_checkpoint_num -gt $last_checkpoint_num ]; then
	echo "Found newer checkpoints in fields/ directory (up to f$(printf "%05d" $fields_checkpoint_num))"
	last_checkpoint_num=$fields_checkpoint_num
fi

# Determine restart file and time
if [ ! -z "$slurm_checkpoint_file" ] && [ ! -z "$slurm_checkpoint_time" ]; then
	# Use info from slurm output
	restart_time="$slurm_checkpoint_time"
	echo "Using checkpoint info from slurm output:"
	echo "  Time: $restart_time"
	startValue=$restart_time
elif [ $last_checkpoint_num -gt 0 ]; then
	echo "Could not extract time from slurm output"
	echo "Using configured startValue=$startValue"
else
	echo "No previous checkpoint found. Starting from initial conditions."
fi

# Copy the latest checkpoint if one exists
if [ $last_checkpoint_num -gt 0 ]; then
	# Try fields directory first, then current directory
	latest_field="fields/${nekcase}.f$(printf "%05d" $last_checkpoint_num)"
	latest_current="${nekcase}.f$(printf "%05d" $last_checkpoint_num)"

	if [ -f "$latest_field" ]; then
		cp "$latest_field" "${nekcase}.f00001"
		echo "Copied latest checkpoint: $latest_field -> ${nekcase}.f00001"
	elif [ -f "$latest_current" ]; then
		cp "$latest_current" "${nekcase}.f00001"
		echo "Copied latest checkpoint: $latest_current -> ${nekcase}.f00001"
	else
		echo "WARNING: Could not find checkpoint file f$(printf "%05d" $last_checkpoint_num)"
	fi
fi

# Always update parameter file to use duct0.f00001
restart_file="${nekcase}.f00001"
# Check if restart file exists (either copied or already present)
if [ -f "$restart_file" ]; then
	has_restart="true"
else
	has_restart="false"
fi
update_par_file "$parfile" "$restart_file" "$startValue" "$has_restart"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# JOB SUBMISSION SETUP
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
echo ""
echo "========================================"
echo "JOB SUBMISSION SETTINGS"
echo "========================================"

final_value=$(echo "$startValue + $siminterval * $numberOfJobs" | bc)
echo "Total number of simulations: $numberOfJobs"
echo "Simulation starts at time value: $startValue seconds"
echo "Final end time value: $final_value seconds"

# Check if the folder exists
if [ ! -d "$location" ]; then
	mkdir -p "$location"
	echo "Folder created: $location"
else
	echo "Folder already exists: $location"
fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# CREATE AND SUBMIT JOBS
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
echo ""
echo "========================================"
echo "PREPARING JOB SUBMISSIONS"
echo "========================================"

for ((nj=1;nj<=${numberOfJobs};nj++)); do
	echo ""
	echo "--- Job $nj/$numberOfJobs ---"

	# Calculate start and end times for this job
	job_start=$(echo "$startValue + ($nj - 1) * $siminterval" | bc)
	job_end=$(echo "$startValue + $nj * $siminterval" | bc)

	# Create job-specific files in location folder
	job_parfile="$location/${nj}_${parfile}"
	job_slurmfile="$location/${nj}_${orgslurmfilename}"

	# Copy parameter file
	cp "$parfile" "$job_parfile"

	# Update parameter file with job-specific settings
	# Always use duct0.f00001 as restart file (will be copied from fields before each job)
	sed -i "s/^endTime.*/endTime = $job_end/" "$job_parfile"

	# For first job, check if restart exists; for subsequent jobs, always use restart
	if [ $nj -eq 1 ]; then
		# First job: check if restart file exists
		if [ -f "${nekcase}.f00001" ]; then
			# Restart exists: uncomment/update startFrom line and remove standalone time
			sed -i "s|^#*startFrom.*|startFrom = ${nekcase}.f00001 time=$job_start|" "$job_parfile"
			sed -i "/^time = /d" "$job_parfile"
		else
			# No restart: comment out startFrom and add time
			sed -i "s|^startFrom.*|#startFrom = ${nekcase}.f00001|" "$job_parfile"
			sed -i "/^time = /d" "$job_parfile"
			sed -i "s|^#startFrom.*|#startFrom = ${nekcase}.f00001\ntime = $job_start|" "$job_parfile"
		fi
	else
		# Subsequent jobs: always use restart (will be copied from previous job output)
		sed -i "s|^#*startFrom.*|startFrom = ${nekcase}.f00001 time=$job_start|" "$job_parfile"
		sed -i "/^time = /d" "$job_parfile"
	fi

	echo "  Time range: $job_start -> $job_end"
	echo "  Parameter file: $job_parfile"

	# Copy and update slurm file
	cp "$orgslurmfilename" "$job_slurmfile"

	# Update job name
	sed -i "s/--job-name=\"[^\"]*\"/--job-name=\"${nj}_${casename}\"/" "$job_slurmfile"
	echo "  Job name: ${nj}_${casename}"
	echo "  Slurm file: $job_slurmfile"

	# Submit job if requested
	if [ $submit_jobs -eq 1 ]; then
		if [ $nj -eq 1 ]; then
			# Submit first job without dependency
			job_id=$(sbatch --parsable "$job_slurmfile")
			echo "  Submitted job ID: $job_id"
		else
			# Submit subsequent jobs with dependency on previous job
			job_id=$(sbatch --parsable --dependency=afterok:$prev_job_id "$job_slurmfile")
			echo "  Submitted job ID: $job_id (depends on $prev_job_id)"
		fi
		prev_job_id=$job_id
	fi
done

echo ""
echo "========================================"
echo "SETUP COMPLETE"
echo "========================================"
if [ $submit_jobs -eq 1 ]; then
	echo "All jobs have been submitted!"
else
	echo "Job files created in $location/"
	echo "Set submit_jobs=1 to automatically submit jobs"
	echo "Or manually submit jobs from $location/"
fi
