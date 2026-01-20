#!/bin/bash

#SBATCH --job-name="1_tw5-9000" 		# Name of the job for checking
#SBATCH --time=96:00:00                 # Wall clock time requested hh:mm:ss
#SBATCH --partition=compute-p2          # Which partition?
#SBATCH --account=research-abe-ur       # Account to charge
#SBATCH --mem-per-cpu=3G                # Amount of memory per CPU
#SBATCH --cpus-per-task=1               # Number of CPUs per task
#SBATCH -n 512                          # Number of CPUs

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# SETUP AND VALIDATION
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

# Extract job number from job name (format: N_casename)
JOB_NUM=$(echo $SLURM_JOB_NAME | cut -d'_' -f1)

# Validate job number
if ! [[ "$JOB_NUM" =~ ^[0-9]+$ ]]; then
	echo "ERROR: Could not extract valid job number from SLURM_JOB_NAME: $SLURM_JOB_NAME"
	echo "Expected format: N_casename (e.g., 1_tw5-9000)"
	exit 1
fi

echo "========================================="
echo "JOB $JOB_NUM STARTING"
echo "Job Name: $SLURM_JOB_NAME"
echo "========================================="

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# COPY PARAMETER FILE
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

PARFILE_SOURCE="inputFiles/${JOB_NUM}_duct.par"
PARFILE_DEST="duct.par"

echo ""
echo "**PARAMETER FILE SETUP**"
if [ -f "$PARFILE_SOURCE" ]; then
	cp "$PARFILE_SOURCE" "$PARFILE_DEST"
	echo "Copied: $PARFILE_SOURCE -> $PARFILE_DEST"
	echo "Settings:"
	grep "startFrom\|endTime" "$PARFILE_DEST"
else
	echo "ERROR: Parameter file not found: $PARFILE_SOURCE"
	exit 1
fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# COPY RESTART CHECKPOINT (for jobs > 1)
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

echo ""
echo "**RESTART FILE SETUP**"
if [ "$JOB_NUM" -eq 1 ]; then
	echo "Job 1: Starting from initial conditions"
	# Verify initial checkpoint exists if not starting from scratch
	if grep -q "startFrom.*duct0\.f00001" "$PARFILE_DEST"; then
		if [ ! -f "duct0.f00001" ]; then
			echo "WARNING: Parameter file references duct0.f00001 but file not found"
			echo "Make sure initial conditions are available or update parameter file"
		fi
	fi
else
	echo "Job $JOB_NUM: Looking for restart file from previous job"

	# Check if fields directory exists
	if [ ! -d "fields" ]; then
		echo "ERROR: fields directory not found!"
		echo "Previous job may have failed or not completed archiving"
		exit 1
	fi

	# Find the latest checkpoint file in fields directory
	LATEST_CHECKPOINT=$(ls -v fields/duct0.f[0-9]* 2>/dev/null | tail -1)

	if [ -f "$LATEST_CHECKPOINT" ]; then
		cp "$LATEST_CHECKPOINT" "duct0.f00001"
		echo "Copied restart file: $LATEST_CHECKPOINT -> duct0.f00001"

		# Verify the file was copied successfully
		if [ ! -f "duct0.f00001" ]; then
			echo "ERROR: Failed to copy restart file"
			exit 1
		fi
	else
		echo "ERROR: No restart file found in fields/ directory"
		echo "Available files:"
		ls -lh fields/ 2>/dev/null || echo "  (none)"
		exit 1
	fi
fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# RUN SIMULATION
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

echo ""
echo "**LOADING MODULES**"
module load DefaultModules slurm/current 2024r1 openmpi/4.1.6

echo ""
echo "**RUNNING NEK5000**"
echo "Start time: $(date)"
srun nek5000
NEK_EXIT_CODE=$?

echo "End time: $(date)"
echo "Nek5000 exit code: $NEK_EXIT_CODE"

if [ $NEK_EXIT_CODE -ne 0 ]; then
	echo "ERROR: Nek5000 exited with error code $NEK_EXIT_CODE"
	exit $NEK_EXIT_CODE
fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# ARCHIVE CHECKPOINT FILES
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

echo ""
echo "**ARCHIVING CHECKPOINT FILES**"

# Ensure fields directory exists
mkdir -p fields

# Find the highest numbered checkpoint file currently in fields/
MAX_FIELD_NUM=0
for file in fields/duct0.f[0-9]*; do
	if [ -f "$file" ]; then
		filename=$(basename "$file")
		num=$(echo "$filename" | sed "s/duct0.f0*//")
		if [ ! -z "$num" ] && [ "$num" -gt "$MAX_FIELD_NUM" ]; then
			MAX_FIELD_NUM=$num
		fi
	fi
done

echo "Current max checkpoint number in fields/: $MAX_FIELD_NUM"

# Rename and move all generated checkpoint files with incremented numbers
CHECKPOINT_COUNT=0
NEXT_NUM=$((MAX_FIELD_NUM + 1))

# First, collect all checkpoint files and sort them
CHECKPOINT_FILES=($(ls -v duct0.f[0-9]* 2>/dev/null))

for checkpoint in "${CHECKPOINT_FILES[@]}"; do
	if [ -f "$checkpoint" ]; then
		NEW_NAME="duct0.f$(printf "%05d" $NEXT_NUM)"
		mv "$checkpoint" "fields/$NEW_NAME"
		echo "  Archived: $checkpoint -> fields/$NEW_NAME"
		CHECKPOINT_COUNT=$((CHECKPOINT_COUNT + 1))
		NEXT_NUM=$((NEXT_NUM + 1))
	fi
done

echo ""
if [ $CHECKPOINT_COUNT -gt 0 ]; then
	echo "Successfully archived $CHECKPOINT_COUNT checkpoint file(s)"
	echo "Latest checkpoint: $(ls -v fields/duct0.f[0-9]* 2>/dev/null | tail -1)"
else
	echo "WARNING: No checkpoint files were generated by this run"
	echo "This may indicate a problem with the simulation"
fi

# Summary of fields directory
echo ""
echo "Fields directory summary:"
echo "  Total files: $(ls -1 fields/duct0.f[0-9]* 2>/dev/null | wc -l)"
echo "  Disk usage: $(du -sh fields/ 2>/dev/null | cut -f1)"

echo ""
echo "========================================="
echo "JOB $JOB_NUM COMPLETED SUCCESSFULLY"
echo "========================================="
