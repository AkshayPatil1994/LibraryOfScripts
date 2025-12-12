import xarray as xr
import time
import os
import sys
import numpy as np
from multiprocessing import Pool
import dask

# Configure dask to use synchronous scheduler to avoid conflicts with multiprocessing
dask.config.set(scheduler='synchronous')

#
# INPUT DATA
#
procx, procy = 4, 2                                 # Number of processors in x and y directions
average_last_n = 260                                # Average over last '260' time snapshots
start_exp_num = 27                                  # Starting experiment number   
end_exp_num = 46                                    # Ending experiment number   
num_parallel_workers = 1                            # Number of parallel processes (adjust based on CPU cores)

# # # # # # # # # # # # # # # # # # #
# SINGLE FILE PROCESSING FUNCTION   #
# # # # # # # # # # # # # # # # # # #
def process_single_file(args):
    """
    Process a single file - can be called in parallel.
    Returns processing time for this file.
    """
    ix, iy, exp_num, base_location, param_name, average_last_n = args
    
    filename = f'{base_location}fielddump.{ix:03d}.{iy:03d}.{exp_num}.nc'
    
    sys.stdout.flush()
    stime = time.time()
    
    try:
        # Open dataset WITHOUT dask chunks to avoid conflicts with multiprocessing
        # Each worker process handles its own file independently
        ds = xr.open_dataset(filename)
        n_snapshots = ds.dims['time']
        n_avg = min(average_last_n, n_snapshots)        
        
        # Select last n_avg snapshots
        ds_subset = ds.isel(time=slice(-n_avg, None))
        
        # Calculate time-averaged dataset
        print(f"  Computing mean for {filename}...")
        sys.stdout.flush()
        ds_avg = ds_subset.mean(dim='time')
        
        # Save to file
        outputfilename = f'{param_name}.{ix:03d}.{iy:03d}.{exp_num}.nc'
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(outputfilename)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except FileExistsError:
                # Another process might have created it
                pass
        
        # Remove existing file if it exists
        if os.path.exists(outputfilename):
            os.remove(outputfilename)
        
        print(f"  Writing to {outputfilename}...")
        sys.stdout.flush()
        ds_avg.to_netcdf(outputfilename)
        
        ds.close()
        etime = time.time()
        elapsed = etime - stime
        print(f"✓ Completed {filename} in {elapsed:.3f} seconds")
        sys.stdout.flush()
        
        return (True, elapsed, filename)
        
    except Exception as e:
        print(f"✗ ERROR processing {filename}: {str(e)}")
        sys.stdout.flush()
        return (False, -1, filename)

# # # # # # # # # # # # # # # # #
# SIMPLE PROGRESS BAR FUNCTION  #
# # # # # # # # # # # # # # # # #
def print_progress_bar(current, total, bar_length=40, prefix='Progress'):
    """
    Print a simple progress bar that works with file logging.
    Forces output to flush immediately so it appears in log files.
    """
    percent = float(current) / total
    filled_length = int(bar_length * percent)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
            
    if sys.stdout.isatty():            
        print(f'\r{prefix}: |{bar}| {current}/{total} ({percent*100:.1f}%)', end='', flush=True)
    else:            
        if current == total or current % max(1, total // 10) == 0:
            print(f'{prefix}: |{bar}| {current}/{total} ({percent*100:.1f}%)', flush=True)

#
# Loop over experiment numbers
#
for e_num in range(start_exp_num, end_exp_num + 1):  # Fixed: added +1 to include end_exp_num
    # Format experiment number
    exp_num = f'{e_num:03d}'
    print(f"\n{'='*60}")
    print(f"=== Experiment Number: {exp_num} ===")
    print(f"{'='*60}")
    
    # 
    # Define Data location
    #
    base_location = f'../{exp_num}/fields/'             # Base location where data is stored
    param_name = f'../{exp_num}/analysis/data/tavg'     # Name of the parameter to save data
    
    # Pre-create output directory
    output_dir = os.path.dirname(param_name)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")
    
    # # # # # # # # #
    # MAIN ANALYSIS #
    # # # # # # # # #
    ps_time = time.time()

    total_files = procx * procy
    print(f"\nStarting PARALLEL analysis of {total_files} files...")
    print(f"Using {num_parallel_workers} parallel workers")
    print(f"Averaging last {average_last_n} snapshots\n")
    sys.stdout.flush()

    # Create list of all file tasks (as tuples to pass to process_single_file)
    tasks = [
        (ix, iy, exp_num, base_location, param_name, average_last_n)
        for ix in range(procx) 
        for iy in range(procy)
    ]
    
    # Process files in parallel
    with Pool(processes=num_parallel_workers) as pool:
        results = pool.map(process_single_file, tasks)
    
    pe_time = time.time()
    total_time = pe_time - ps_time
    
    # Summary statistics
    successful_files = sum(1 for success, _, _ in results if success)
    failed_files = sum(1 for success, _, _ in results if not success)
    successful_times = [elapsed for success, elapsed, _ in results if success]
    avg_time_per_file = sum(successful_times) / max(len(successful_times), 1)
    
    print(f"\n{'='*60}")
    print(f"EXPERIMENT {exp_num} SUMMARY:")
    print(f"  Total time: {total_time:.2f} seconds")
    print(f"  Successful files: {successful_files}/{total_files}")
    print(f"  Failed files: {failed_files}")
    if failed_files > 0:
        print(f"  Failed files:")
        for success, _, filename in results:
            if not success:
                print(f"    - {filename}")
    print(f"  Average time per file: {avg_time_per_file:.2f} seconds")
    if successful_files > 0:
        print(f"  Speedup factor: ~{total_files * avg_time_per_file / total_time:.1f}x")
    print(f"{'='*60}")
    sys.stdout.flush()

print(f"\n\n{'='*60}")
print(f"ALL EXPERIMENTS COMPLETED!")
print(f"{'='*60}")
sys.stdout.flush()
