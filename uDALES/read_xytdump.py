import matplotlib.pyplot as plt
import netCDF4 as nc
# USER-DEFINED PARAMETERS
filename = 'xytdump.001.nc'         # Name of the netCDF file to read
Uref = 15.0                         # Reference velocity for normalisation (m/s)
Zref = 0.2                          # Reference height for normalisation (m)
# Plotting parameters   
plot_index_start = 0               # Index to start plotting individual profiles (to avoid startup transients)
avg_index_start = 80                # Index to start calculating the average profile (to avoid startup transients)
#
# LOAD DATA AND PLOT AVERAGE PROFILES
#
ds = nc.Dataset(filename, 'r')
zt   = ds.variables['zt'][:]       # Z locations of the grid points
time = ds.variables['time'][:]     # Time in seconds
uxyt = ds.variables['uxyt'][:]     # Streamwise velocity at the grid points
ds.close()
# FIGURE
plt.figure(1)
plt.plot(uxyt[plot_index_start:, :].T/Uref, zt/Zref,alpha=0.25,color='r')
plt.plot(uxyt[avg_index_start:, :].mean(axis=0)/Uref, zt/Zref, 'ko', markersize=2, label=f'Average profile last {uxyt.shape[0]-avg_index_start} snapshots')
plt.axhline(1.0, color='k', linestyle='--')
plt.axvline(1.0, color='k', linestyle='--')
plt.grid(True)
plt.legend()
plt.xlabel('Streamwise velocity (m/s)')
plt.ylabel('Height (m)')
plt.title('Horizontal-mean u profiles')
plt.show()
