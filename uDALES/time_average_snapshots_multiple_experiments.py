import xarray as xr
import time
import os
import sys
import numpy as np
#
# INPUT DATA
#
procx, procy = 4, 2                                 # Number of processors in x and y directions
average_last_n = 260                                # Average over last '260' time snapshots
start_exp_num = 27                                  # Starting experiment number   
end_exp_num = 46                                    # Starting experiment number   
# Optional parameters 
file_chunks_dask = 10                               # Reduced chunk size for memory efficiency
spatial_chunks = 64                                 # Chunk size for spatial dimensions
verbose_progress = True                             # Show progress bar per processor file
#
# Loop over experiment numbers
#
for e_num in range(start_exp_num,end_exp_num):
    # Format experiment number
    exp_num = f'{e_num:03d}'
    print(f"\n=== Experiment Number: {exp_num} ===")
    # 
    # Define Data location
    #
    base_location = f'../{exp_num}/fields/'             # Based location of the location where data is stored
    param_name = f'../{exp_num}/analysis/data/tavg'     # Name of the parameter to save data (optionally location)
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

    # # # # # # # # #
    # MAIN ANALYSIS #
    # # # # # # # # #
    ps_time = time.time()

    total_files = procx * procy
    file_counter = 0

    print(f"Starting analysis of {total_files} files...")
    print(f"Averaging last {average_last_n} snapshots\n")
    sys.stdout.flush()

    for ix in range(0, procx):
        for iy in range(0, procy):        
            file_counter += 1
            filename = f'{base_location}fielddump.{ix:03d}.{iy:03d}.{exp_num}.nc'
            
            print(f"\n[{file_counter}/{total_files}] Working with {filename} ...")
            sys.stdout.flush()
            stime = time.time()
            
            # Open dataset with chunking on all dimensions
            ds = xr.open_dataset(filename, chunks={'time': file_chunks_dask})
            n_snapshots = ds.dims['time']
            n_avg = min(average_last_n, n_snapshots)        
            spatial_dims = [dim for dim in ds.dims if dim != 'time']
            
            # Rechunk spatial dimensions for memory efficiency
            chunk_dict = {'time': file_chunks_dask}
            for dim in spatial_dims:
                chunk_dict[dim] = min(spatial_chunks, ds.dims[dim])
            
            ds = ds.chunk(chunk_dict)
            
            # Select last n_avg snapshots
            ds_subset = ds.isel(time=slice(-n_avg, None))
            
            print(f"  Computing mean velocities...")
            sys.stdout.flush()
            # Calculate time-averaged velocities and compute immediately
            u_mean = ds_subset['u'].mean(dim='time').compute()
            v_mean = ds_subset['v'].mean(dim='time').compute()
            w_mean = ds_subset['w'].mean(dim='time').compute()
            
            # Create average dataset with all other variables       
            sys.stdout.flush()
            ds_avg = ds_subset.mean(dim='time').compute()
            
            # Save to file
            outputfilename = f'{param_name}.{ix:03d}.{iy:03d}.{exp_num}.nc'
            
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(outputfilename)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Remove existing file if it exists
            if os.path.exists(outputfilename):
                os.remove(outputfilename)
            
            print(f"  Writing to {outputfilename}...")
            sys.stdout.flush()
            # Now everything is computed, so writing should be fast
            ds_avg.to_netcdf(outputfilename)
            
            ds.close()
            etime = time.time()
            print(f"  Completed in {etime-stime:.3f} seconds")
            sys.stdout.flush()
            
            # Update overall progress
            print_progress_bar(file_counter, total_files, prefix='Overall Progress')

    pe_time = time.time()
    print(f"\n\n*** TOTAL TIME: {pe_time-ps_time:.2f} seconds ***")
    sys.stdout.flush()
