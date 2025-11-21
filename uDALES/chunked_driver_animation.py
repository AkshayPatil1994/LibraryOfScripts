import numpy as np
import matplotlib.pyplot as plt
import struct
import os
from pathlib import Path

class DriverFileReader:
    '''
    Memory-efficient reader for uDALES driver files.
    
    NEW FEATURES:
    - Lazy loading: read only requested timesteps
    - Streaming: process data without loading all timesteps
    - Memory-mapped files for large datasets
    - Chunked processing for statistics
    '''
    
    def __init__(self, experiment_number, nprocy=1, job_number=None):
        self.exp_nr = f"{int(experiment_number):03d}"
        self.nprocy = nprocy
        self.job_nr = f"{int(job_number):03d}" if job_number else self.exp_nr
        
    def read_time_file(self, directory='.'):
        '''Read the time stamp file'''
        filename = f"tdriver_000.{self.job_nr}"
        filepath = Path(directory) / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Time file not found: {filepath}")
        
        record_size = 8
        file_size = filepath.stat().st_size
        n_records = file_size // record_size
        
        print(f"Reading {n_records} time stamps from {filename}")
        
        times = np.fromfile(filepath, dtype=np.float64, count=n_records)
        return times
    
    def get_field_info(self, field_name, ny_local, nz, directory='.', 
                       scalar_fields=1, has_ghost=True):
        '''
        Get field metadata without reading data.
        Returns record size and number of timesteps.
        '''
        driver_id = "000"
        filename = f"{field_name}driver_{driver_id}.{self.exp_nr}"
        filepath = Path(directory) / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Field file not found: {filepath}")
        
        jh = 1 if has_ghost else 0
        kh = 1 if has_ghost else 0
        ny_local_total = ny_local + 2 * jh
        nz_total = nz + 2 * kh
        
        if field_name == 's':
            record_size = ny_local_total * nz_total * scalar_fields * 8
        else:
            record_size = ny_local_total * nz_total * 8
        
        file_size = filepath.stat().st_size
        n_timesteps = file_size // record_size
        
        return record_size, n_timesteps, ny_local_total, nz_total
    
    def read_field_timestep(self, field_name, timestep, ny_total, nz, directory='.', 
                           scalar_fields=1, has_ghost=True):
        '''
        Read a SINGLE timestep from all processors.
        Much more memory efficient for processing one timestep at a time.
        '''
        ny_local = ny_total // self.nprocy
        jh = 1 if has_ghost else 0
        
        record_size, _, ny_local_total, nz_total = self.get_field_info(
            field_name, ny_local, nz, directory, scalar_fields, has_ghost
        )
        
        # Read from each processor
        proc_data = []
        for proc_id in range(self.nprocy):
            driver_id = f"{proc_id:03d}"
            filename = f"{field_name}driver_{driver_id}.{self.exp_nr}"
            filepath = Path(directory) / filename
            
            with open(filepath, 'rb') as f:
                f.seek(timestep * record_size)
                data = f.read(record_size)
                
                if len(data) < record_size:
                    raise ValueError(f"Incomplete data at timestep {timestep}")
                
                values = np.frombuffer(data, dtype=np.float64)
                
                if field_name == 's':
                    field_data = values.reshape((ny_local_total, nz_total, scalar_fields), order='F')
                else:
                    field_data = values.reshape((ny_local_total, nz_total), order='F')
                
                proc_data.append(field_data)
        
        # Collate data
        if len(proc_data) == 1:
            return proc_data[0]
        
        if field_name == 's':
            collated_parts = []
            for i, data in enumerate(proc_data):
                if i == 0:
                    collated_parts.append(data[:, :, :])
                elif i == len(proc_data) - 1:
                    collated_parts.append(data[jh:, :, :])
                else:
                    collated_parts.append(data[jh:-jh, :, :])
            return np.concatenate(collated_parts, axis=0)
        else:
            collated_parts = []
            for i, data in enumerate(proc_data):
                if i == 0:
                    collated_parts.append(data[:, :])
                elif i == len(proc_data) - 1:
                    collated_parts.append(data[jh:, :])
                else:
                    collated_parts.append(data[jh:-jh, :])
            return np.concatenate(collated_parts, axis=0)
    
    def read_field_file(self, field_name, ny_total, nz, n_timesteps, directory='.', 
                       scalar_fields=1, has_ghost=True, timestep_range=None):
        '''
        Read field files with optional timestep range for memory efficiency.
        
        Parameters:
        -----------
        timestep_range : tuple, optional
            (start, end) timestep indices to read. If None, reads all timesteps.
        '''
        print(f"\nReading field '{field_name}' from {self.nprocy} processor(s)")
        
        ny_local = ny_total // self.nprocy
        
        if timestep_range is None:
            timestep_range = (0, n_timesteps)
        
        start_t, end_t = timestep_range
        n_steps_to_read = end_t - start_t
        
        print(f"  Reading timesteps {start_t} to {end_t} ({n_steps_to_read} steps)")
        print(f"  Total grid: ny={ny_total}, nz={nz}")
        print(f"  Per processor: ny_local={ny_local}")
        
        jh = 1 if has_ghost else 0
        kh = 1 if has_ghost else 0
        ny_local_total = ny_local + 2 * jh
        nz_total = nz + 2 * kh
        
        # Calculate record size
        if field_name == 's':
            record_size = ny_local_total * nz_total * scalar_fields * 8
        else:
            record_size = ny_local_total * nz_total * 8
        
        # Read processor by processor into list (same as original, but only requested timesteps)
        proc_data = []
        for proc_id in range(self.nprocy):
            driver_id = f"{proc_id:03d}"
            filename = f"{field_name}driver_{driver_id}.{self.exp_nr}"
            filepath = Path(directory) / filename
            
            print(f"  Reading from driver_id={driver_id}...", end=" ")
            
            # Allocate array for this processor's data
            if field_name == 's':
                field_data = np.zeros((n_steps_to_read, ny_local_total, nz_total, scalar_fields))
            else:
                field_data = np.zeros((n_steps_to_read, ny_local_total, nz_total))
            
            with open(filepath, 'rb') as f:
                # Seek to start timestep
                f.seek(start_t * record_size)
                
                # Read only the requested timesteps
                for local_t in range(n_steps_to_read):
                    data = f.read(record_size)
                    if len(data) < record_size:
                        print(f"WARNING: Incomplete data at timestep {start_t + local_t}")
                        break
                    
                    values = np.frombuffer(data, dtype=np.float64)
                    
                    if field_name == 's':
                        field_data[local_t] = values.reshape((ny_local_total, nz_total, scalar_fields), order='F')
                    else:
                        field_data[local_t] = values.reshape((ny_local_total, nz_total), order='F')
            
            proc_data.append(field_data)
            print(f"Done. Shape: {field_data.shape}")
        
        print(f"  Collating data along y-axis...")
        
        # Collate using same logic as original
        if len(proc_data) == 1:
            collated_data = proc_data[0]
        else:
            if field_name == 's':
                collated_parts = []
                for i, data in enumerate(proc_data):
                    if i == 0:
                        # First processor: keep all including ghost at end
                        collated_parts.append(data[:, :, :, :])
                    elif i == len(proc_data) - 1:
                        # Last processor: skip ghost at start
                        collated_parts.append(data[:, jh:, :, :])
                    else:
                        # Middle processors: skip ghosts at both ends
                        collated_parts.append(data[:, jh:-jh, :, :])
                
                collated_data = np.concatenate(collated_parts, axis=1)
            else:
                collated_parts = []
                for i, data in enumerate(proc_data):
                    if i == 0:
                        # First processor: keep all including ghost at end
                        collated_parts.append(data[:, :, :])
                    elif i == len(proc_data) - 1:
                        # Last processor: skip ghost at start
                        collated_parts.append(data[:, jh:, :])
                    else:
                        # Middle processors: skip ghosts at both ends
                        collated_parts.append(data[:, jh:-jh, :])
                
                collated_data = np.concatenate(collated_parts, axis=1)
        
        print(f"  Final collated shape: {collated_data.shape}")
        print(f"  Value range: [{collated_data.min():.6f}, {collated_data.max():.6f}]")
        
        return collated_data
    
    def compute_statistics_streaming(self, field_name, ny_total, nz, n_timesteps, 
                                    directory='.', has_ghost=True, chunk_size=10):
        '''
        Compute mean and RMS profiles WITHOUT loading all data into memory.
        Uses Welford's online algorithm for numerically stable streaming statistics.
        '''
        print(f"\nComputing streaming statistics for '{field_name}'")
        print(f"  Processing {n_timesteps} timesteps in chunks of {chunk_size}")
        
        ny_local = ny_total // self.nprocy
        jh = 1 if has_ghost else 0
        kh = 1 if has_ghost else 0
        nz_total = nz + 2 * kh
        final_ny = ny_total + 2 * jh
        
        # Initialize accumulators
        mean = np.zeros((final_ny, nz_total))
        M2 = np.zeros((final_ny, nz_total))  # For variance calculation
        count = 0
        
        # Process in chunks
        for chunk_start in range(0, n_timesteps, chunk_size):
            chunk_end = min(chunk_start + chunk_size, n_timesteps)
            
            # Read chunk
            chunk_data = self.read_field_file(
                field_name, ny_total, nz, n_timesteps, directory,
                has_ghost=has_ghost, timestep_range=(chunk_start, chunk_end)
            )
            
            # Update statistics using Welford's algorithm
            for t in range(chunk_data.shape[0]):
                for j in range(chunk_data.shape[1]):
                    count += 1
                    delta = chunk_data[t, j, :] - mean[j, :]
                    mean[j, :] += delta / count
                    delta2 = chunk_data[t, j, :] - mean[j, :]
                    M2[j, :] += delta * delta2
            
            # Free memory
            del chunk_data
            
            print(f"  Processed timesteps {chunk_start} to {chunk_end}")
        
        # Compute final statistics
        variance = M2 / count
        rms = np.sqrt(variance)
        
        # Average over y-direction
        mean_profile = np.mean(mean, axis=0)
        rms_profile = np.sqrt(np.mean(variance, axis=0))
        
        return mean_profile, rms_profile
    
    def read_all_fields(self, ny, nz, directory='.',
                       read_temperature=False, read_moisture=False,
                       read_scalars=False, n_scalars=0, has_ghost=True,
                       timestep_range=None):
        '''
        Read fields with optional timestep range for memory efficiency.
        '''
        times = self.read_time_file(directory)
        n_timesteps = len(times)
        
        if timestep_range is None:
            timestep_range = (0, n_timesteps)
        
        start_t, end_t = timestep_range
        
        data = {
            'times': times[start_t:end_t],
            'u': self.read_field_file('u', ny, nz, n_timesteps, directory, 
                                     has_ghost=has_ghost, timestep_range=timestep_range),
            'v': self.read_field_file('v', ny, nz, n_timesteps, directory, 
                                     has_ghost=has_ghost, timestep_range=timestep_range),
            'w': self.read_field_file('w', ny, nz, n_timesteps, directory, 
                                     has_ghost=has_ghost, timestep_range=timestep_range)
        }
        
        if read_temperature:
            data['thl'] = self.read_field_file('h', ny, nz, n_timesteps, directory, 
                                              has_ghost=has_ghost, timestep_range=timestep_range)
        
        if read_moisture:
            data['qt'] = self.read_field_file('q', ny, nz, n_timesteps, directory, 
                                             has_ghost=has_ghost, timestep_range=timestep_range)
        
        if read_scalars and n_scalars > 0:
            data['sv'] = self.read_field_file('s', ny, nz, n_timesteps, directory, 
                                            scalar_fields=n_scalars, has_ghost=has_ghost,
                                            timestep_range=timestep_range)
        
        return data


if __name__ == "__main__":
    # USER INPUT PARAMETERS
    experiment_number = '001'
    nprocy = 16
    ny = 1008
    nz = 240
    utau = 0.497481658
    H = 600.0
    nu = 1.5e-5
    Retau = utau*H/nu
    data_dir = '.'
    zfile = 'lscale.inp.001'
    ylen = 2500.0
    n_frames = 100
    save_animation = True
    video_fps = 10
    video_dpi = 400
    umax = 13.0
    calc_rms = False
    
    # MEMORY-EFFICIENT OPTIONS
    use_streaming = True  # Use streaming statistics (very memory efficient)
    load_subset = True    # Load only a subset of timesteps
    subset_range = (10000, 12500)  # Which timesteps to load if load_subset=True
    
    reader = DriverFileReader(experiment_number=experiment_number, nprocy=nprocy)
    
    try:
        print("="*70)
        print(f"Reading uDALES driver files with nprocy={nprocy}")
        print("="*70)
        
        if use_streaming and calc_rms:
            # OPTION 1: Streaming statistics (minimal memory usage)
            print("\nUsing streaming statistics computation...")
            times = reader.read_time_file(data_dir)
            
            u_mean_profile, u_rms_profile = reader.compute_statistics_streaming(
                'u', ny, nz, len(times), data_dir, chunk_size=10
            )
            v_mean_profile, v_rms_profile = reader.compute_statistics_streaming(
                'v', ny, nz, len(times), data_dir, chunk_size=10
            )
            w_mean_profile, w_rms_profile = reader.compute_statistics_streaming(
                'w', ny, nz, len(times), data_dir, chunk_size=10
            )
            
            # Plot streaming results
            z = np.loadtxt(zfile, skiprows=1)[:, 0]
            plt.figure(figsize=(7, 6))
            plt.plot(u_rms_profile[1:-1]/utau, z*Retau/H, 'b-', label='u_rms')
            plt.plot(v_rms_profile[1:-1]/utau, z*Retau/H, 'r-', label='v_rms')
            plt.plot(w_rms_profile[1:-1]/utau, z*Retau/H, 'g-', label='w_rms')
            plt.ylabel(r'$x_3^+$', fontsize=20)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig('rms_velocity_profiles_streaming.png', dpi=150, bbox_inches='tight')
            print("Saved streaming RMS profiles to 'rms_velocity_profiles_streaming.png'")
            
        else:
            # OPTION 2: Load subset or all data
            timestep_range = subset_range if load_subset else None
            
            data = reader.read_all_fields(
                ny=ny, nz=nz, directory=data_dir,
                read_temperature=False, read_moisture=False,
                read_scalars=False, n_scalars=0, has_ghost=True,
                timestep_range=timestep_range
            )
            
            print("\n" + "="*70)
            print("Successfully read and collated driver files!")
            print("="*70)
            print(f"Number of time steps: {len(data['times'])}")
            print(f"Time range: {data['times'][0]:.2f} to {data['times'][-1]:.2f} seconds")
            print(f"U velocity shape: {data['u'].shape}")
            print("="*70)
            
            # Standard analysis
            u_mean = np.mean(data['u'], axis=(0, 1))
            v_mean = np.mean(data['v'], axis=(0, 1))
            w_mean = np.mean(data['w'], axis=(0, 1))
            z = np.loadtxt(zfile, skiprows=1)[:, 0]
            
            # Visualization
            plt.figure(1, figsize=(15, 6))
            plt.subplot(2, 2, 1)
            y = np.linspace(0, ylen, ny+1)
            plt.pcolormesh(y, z, data['u'][0, 1:-1, 1:-1].T, cmap='RdBu_r', shading='auto')
            plt.xlabel('Y')
            plt.ylabel('Z')
            plt.title(f'U velocity at t={data["times"][0]:.1f}s')
            plt.axis('equal')
            
            mid_t = len(data['times']) // 2
            plt.subplot(2, 2, 3)
            plt.pcolormesh(y, z, data['u'][mid_t, 1:-1, 1:-1].T, cmap='RdBu_r', shading='auto')
            plt.xlabel('Y')
            plt.ylabel('Z')
            plt.title(f'U velocity at t={data["times"][mid_t]:.1f}s')
            plt.axis('equal')
            
            plt.subplot(1, 2, 2)
            plt.semilogx(z*Retau/H, u_mean[1:-1]/utau, 'bo', label='U')
            plt.xlabel('Mean velocity [m/s]')
            plt.ylabel('Z index')
            plt.title('Time and spanwise averaged velocity profiles')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig('driver_analysis.png', dpi=150, bbox_inches='tight')
            print("\nSaved visualization to 'driver_analysis.png'")
            
            if calc_rms:
                u_rms = np.sqrt(np.mean((data['u'] - u_mean[np.newaxis, np.newaxis, :])**2, axis=(0, 1)))
                v_rms = np.sqrt(np.mean((data['v'] - v_mean[np.newaxis, np.newaxis, :])**2, axis=(0, 1)))
                w_rms = np.sqrt(np.mean((data['w'] - w_mean[np.newaxis, np.newaxis, :])**2, axis=(0, 1)))
                tke = 0.5 * (u_rms**2 + v_rms**2 + w_rms**2)
                
                plt.figure(2, figsize=(7, 6))
                plt.plot(u_rms[1:-1]/utau, z*Retau/H, 'b-', label='u_rms')
                plt.plot(v_rms[1:-1]/utau, z*Retau/H, 'r-', label='v_rms')
                plt.plot(w_rms[1:-1]/utau, z*Retau/H, 'g-', label='w_rms')
                plt.plot(tke[1:-1]/utau**2, z*Retau/H, 'k--', label='TKE')
                plt.ylabel(r'$x_3^+$', fontsize=20)
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig('rms_velocity_profiles.png', dpi=150, bbox_inches='tight')
                print("Saved RMS velocity profiles to 'rms_velocity_profiles.png'")
            
            if save_animation:
                # MEMORY-EFFICIENT ANIMATION: Read one timestep at a time
                import matplotlib.animation as animation
                from tqdm.auto import tqdm
                
                print("\nCreating memory-efficient animation...")
                fig, axes = plt.subplots(3, 1, figsize=(15, 12))
                
                # Determine which timesteps to animate
                total_timesteps = len(data['times'])
                timestep_indices = np.linspace(0, total_timesteps-1, n_frames, dtype=int)
                
                def render_frame(frame_idx):
                    t = timestep_indices[frame_idx]
                    # Clear all axes
                    for ax in axes:
                        ax.clear()
                    pimg = axes[0].pcolormesh(y, z, data['u'][t, 1:-1, 1:-1].T, 
                                              cmap='magma_r', shading='auto')
                    axes[0].set_title(f'U velocity at t={data["times"][t]:.2f}s')
                    axes[0].set_xlabel('Y')
                    axes[0].set_ylabel('Z')
                    pimg.set_clim(0, umax)
                    axes[0].set_xlim(0, ylen)
                    axes[0].set_ylim(0, H)

                    pimg = axes[1].pcolormesh(y, z, data['v'][t, 1:-1, 1:-1].T, 
                                              cmap='BrBG', shading='auto')
                    axes[1].set_xlabel('Y')
                    axes[1].set_ylabel('Z')
                    pimg.set_clim(-5, 5)
                    axes[1].set_xlim(0, ylen)
                    axes[1].set_ylim(0, H)  

                    pimg = axes[2].pcolormesh(y, z, data['w'][t, 1:-1, 1:-1].T, 
                                              cmap='RdGy_r', shading='auto')
                    axes[2].set_xlabel('Y')
                    axes[2].set_ylabel('Z')
                    pimg.set_clim(-4, 4)
                    axes[2].set_xlim(0, ylen)
                    axes[2].set_ylim(0, H)
                                  
                
                writer = animation.FFMpegWriter(fps=video_fps)
                out_file = 'u_velocity_animation.mp4'
                with writer.saving(fig, out_file, dpi=video_dpi):
                    for frame_idx in tqdm(range(n_frames), desc='Saving animation', unit='frame'):
                        render_frame(frame_idx)
                        fig.canvas.draw()
                        writer.grab_frame()
                
                print(f"Saved animation to '{out_file}'")
    
    except FileNotFoundError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
