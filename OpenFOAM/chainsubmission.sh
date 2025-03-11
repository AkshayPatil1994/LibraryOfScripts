#!/bin/bash
# submit_jobs.sh - Script to submit multiple OpenFOAM simulations with varying parameters
# This script creates multiple independent chains of jobs with controlled parallelism
# Usage: ./submit_jobs.sh [--dry-run]

# Define arrays of possible values for each parameter
# You can modify these arrays to include your desired parameter values

# UQ 16 angles
#runtypes=("UQ_16")
#inflow_angles=(26 46 71 90 139 154 181 195 198 226 230 255 275 295 313 353)

# UQ 40 angles
runtypes=("UQ_40")
inflow_angles=(10 25 39 43 52 54 67 81 84 104 107 133 152 160 163 173 181 187 191 196 204 207 216 219 226 226.5 233 240 243 253 258 265 278 283 293 308 312 329 342 356)

#meshnames=("mesh1" "mesh3" "mesh4")
meshnames=("mesh4")

# Path to your SLURM template file
TEMPLATE_FILE="template.slurm"

# Maximum number of concurrent job chains
MAX_CONCURRENT_CHAINS=10

# Create a directory for job scripts if it doesn't exist
SCRIPTS_DIR="job_scripts"
mkdir -p "$SCRIPTS_DIR"

##################################################################################
# DO NOT TOUCH THINGS BELOW UNLESS YOU ARE ABOSLUTELY SURE OF WHAT YOU ARE DOING #
##################################################################################

# Check for dry run mode
DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo "*** DRY RUN MODE: Will create job scripts but not submit them ***"
fi

# Check if template file exists
if [[ ! -f "$TEMPLATE_FILE" ]]; then
    echo "Error: Template file not found: $TEMPLATE_FILE"
    exit 1
fi

# Generate all job combinations
job_combinations=()
for runtype in "${runtypes[@]}"; do
    for angle in "${inflow_angles[@]}"; do
        # Create the inflowdegree with "_degrees" suffix
        inflowdegree="${angle}_degrees"
        
        for meshname in "${meshnames[@]}"; do
            # Create a unique job name
            job_name="${runtype}_${inflowdegree}_${meshname}"
            job_combinations+=("$runtype|$inflowdegree|$meshname|$job_name")
        done
    done
done

# Total number of jobs
total_jobs=${#job_combinations[@]}
echo "Total jobs to process: $total_jobs"

# Calculate how many combinations to process per chain
combinations_per_chain=$(( (total_jobs + MAX_CONCURRENT_CHAINS - 1) / MAX_CONCURRENT_CHAINS ))
echo "Jobs per chain: $combinations_per_chain (approximately)"

# Arrays to store information
declare -a chain_last_job_ids      # Last job ID of each chain
declare -a all_job_files           # All job script filenames
declare -a all_job_commands        # All sbatch commands
declare -a all_job_names           # All job names
declare -a chain_job_files         # Job files by chain
declare -a first_chain_jobs        # First job in each chain

# Total job counter
job_count=0

# Create and process job chains
for ((chain=0; chain<MAX_CONCURRENT_CHAINS; chain++)); do
    echo "Creating job chain #$((chain+1)):"
    
    # Initialize array for this chain's job files
    chain_job_files[$chain]=""
    
    # Previous job ID in this chain (initially empty)
    prev_job_id=""
    
    # Process each job in this chain
    for ((i=0; i<combinations_per_chain; i++)); do
        # Calculate the index in the job_combinations array
        combination_idx=$((chain + (i * MAX_CONCURRENT_CHAINS)))
        
        # Skip if we've processed all combinations
        if [ $combination_idx -ge $total_jobs ]; then
            break
        fi
        
        # Extract parameters for this job
        job_info="${job_combinations[$combination_idx]}"
        IFS="|" read -r runtype inflowdegree meshname job_name <<< "$job_info"
        
        # Create job script
        script_file="${SCRIPTS_DIR}/${job_name}.slurm"
        cp "$TEMPLATE_FILE" "$script_file"
        
        # Replace the job name in the SLURM header
        sed -i "s/#SBATCH --job-name=\"mesh_1\"/#SBATCH --job-name=\"${job_name}\"/g" "$script_file"
        
        # Replace the parameter values
        sed -i "s/runtype=\"UQ_16\"/runtype=\"${runtype}\"/g" "$script_file"
        sed -i "s/inflowdegree=\"46_degrees\"/inflowdegree=\"${inflowdegree}\"/g" "$script_file"
        sed -i "s/meshname=\"mesh1\"/meshname=\"${meshname}\"/g" "$script_file"
        
        # Increment the simulation number
        sed -i "s/simNum=[0-9]\+/simNum=$((job_count + 1))/g" "$script_file"
        
        # Store job information
        all_job_files[$job_count]="$script_file"
        all_job_names[$job_count]="$job_name"
        
        # Append to this chain's job files
        if [ -z "${chain_job_files[$chain]}" ]; then
            chain_job_files[$chain]="$script_file"
        else
            chain_job_files[$chain]="${chain_job_files[$chain]},$script_file"
        fi
        
        # Prepare the submission command
        if [ -z "$prev_job_id" ]; then
            # First job in this chain - no dependency
            sbatch_cmd="sbatch $script_file"
            echo "  Job: $job_name ($((job_count + 1))/$total_jobs)"
            echo "    No dependency (first in chain)"
            
            # Save this as the first job in the chain
            first_chain_jobs[$chain]="$script_file"
        else
            # Add dependency on the previous job in this chain
            if [ "$DRY_RUN" = true ]; then
                # For dry-run, use placeholder job IDs
                sbatch_cmd="sbatch --dependency=afterok:PREV_JOB_${chain}_${i-1} $script_file"
            else
                sbatch_cmd="sbatch --dependency=afterok:$prev_job_id $script_file"
            fi
            echo "  Job: $job_name ($((job_count + 1))/$total_jobs)"
            echo "    Depends on previous job in chain"
        fi
        
        all_job_commands[$job_count]="$sbatch_cmd"
        
        # If not in dry-run mode, submit the job
        if [ "$DRY_RUN" = false ]; then
            current_job_id=$(eval $sbatch_cmd | awk '{print $4}')
            echo "    Submitted as job ID: $current_job_id"
            
            # Update previous job ID for the next iteration in this chain
            prev_job_id=$current_job_id
        else
            # In dry-run mode, just simulate a job ID
            prev_job_id="PREV_JOB_${chain}_${i}"
        fi
        
        # Increment total job counter
        job_count=$((job_count + 1))
        
        # Short delay to avoid overwhelming the scheduler
        if [ "$DRY_RUN" = false ]; then
            sleep 0.2
        fi
    done
    
    # Save the last job ID of this chain
    if [ -n "$prev_job_id" ]; then
        chain_last_job_ids[$chain]=$prev_job_id
    fi
    
    echo "  Chain #$((chain+1)) complete"
    echo ""
done

if [ "$DRY_RUN" = true ]; then
    echo "================ DRY RUN SUMMARY ================"
    echo "Created $job_count job scripts in $SCRIPTS_DIR/"
    echo ""
    echo "Initial concurrent jobs that would be submitted:"
    for ((chain=0; chain<MAX_CONCURRENT_CHAINS; chain++)); do
        if [ -n "${first_chain_jobs[$chain]}" ]; then
            echo "sbatch ${first_chain_jobs[$chain]}"
        fi
    done
    echo ""
    echo "To submit all jobs with proper dependencies, run:"
    echo "./arrayjobsubmission.sh"
    echo ""
    echo "To manually submit only one job, use the individaul job script."
    echo "For example, to submit only the first job of the first chain:"
    echo "sbatch ${first_chain_jobs[0]}"
    echo ""
    echo "Job chains overview:"
    for ((chain=0; chain<MAX_CONCURRENT_CHAINS; chain++)); do
        if [ -n "${chain_job_files[$chain]}" ]; then
            chain_jobs=$(echo ${chain_job_files[$chain]} | tr ',' ' ')
            echo "Chain $((chain+1)): $(echo $chain_jobs | wc -w) jobs"
        fi
    done
else
    echo "Job submission complete. Total jobs submitted: $job_count"
    echo ""
    echo "IMPORTANT NOTES:"
    echo "1. Jobs are organized into $MAX_CONCURRENT_CHAINS independent chains"
    echo "2. If a job fails, only subsequent jobs in the same chain will be affected"
    echo "3. Other chains will continue regardless of failures in different chains"
    echo ""
    echo "To check the status of all submitted jobs, run:"
    echo "squeue --me"
fi
