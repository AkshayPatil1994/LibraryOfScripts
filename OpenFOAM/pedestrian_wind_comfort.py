############################################
# Script that calculates the Comfort Class #
############################################
from tqdm import tqdm
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
#
# USER INPUT PARAMETERS
#
z_comfort = 2.0                                           # Height of the comfort class (m)
comfort_class_filename = 'denhaag/comfort_class_lod1p2'   # Name of the output file
# Path to the weather station data
wind_datafilename = 'data/denhaag.dat'
sim_file_prefix = 'Umag_2'
# Log-Law profile parameters
zreference = 10.0                               # Reference height (m)
boundary_condition_value = 5.0                  # Boundary condition used for the simulation (m/s)
z0 = 0.5                                        # Roughness length (m)
kappa = 0.41                                    # von Karman constant
Cmu = 0.09                                      # k-Epsilon constant
exceedance_value = 5.0                          # This is according to NEN8100 - Maybe different for other cases
number_of_wind_directions = 360                 # Number of wind directions (degrees)
#
# FILE CONFIGURATION
#
print("***********************************************")
print("********* Loading weather station data ********")
print("***********************************************")
print(f"--- WORKING FOR: {comfort_class_filename}")
# 
# Fetch the wind speed and direction
#
data = np.loadtxt(wind_datafilename)
wind_speed = data[:,1]/10.0                     # Rescale data to m/s from 0.1 m/s
wind_direction = data[:,0]
print(f"Historical Wind Dataframe size: {len(data)}")
print(f"Minimum speed: {np.min(wind_speed)} | Maximum speed: {np.max(wind_speed)}")
# Clear memory
del data
#
# Now load all the wind magnitude data
#
def readdata(filename):
    with open(filename, 'rb') as f:
        f.seek(0)
        data = np.fromfile(f, dtype=np.float64)
    return data
# Read all data into a single dataframe for easy access
setup_data = True
print("*** Loading the simulation data to memory ***")
time1 = time.time()
for wind_index in range(1,number_of_wind_directions):    
    tempdata = readdata(f'{sim_file_prefix}_{wind_index}.bin')    
    if(setup_data):       
        data_size = np.shape(tempdata)[0]        
        simulation_data = np.zeros((number_of_wind_directions,data_size))
        setup_data = False
    # Assign the data to the correct wind direction
    simulation_data[wind_index-1,:] = tempdata    
print(f"*** Simulation data loaded in {time.time()-time1:.2f} seconds ***")
# 
# Now we can calculate the comfort class
#
print("NOTICE: The comfort class calculations rounds the wind direction to the nearest integer value!")
ustar = (boundary_condition_value*kappa)/(np.log((zreference+z0)/z0))
norm_U = (ustar/kappa)*np.log((z_comfort+z0)/z0) 
# Normalise the simulation data by the boundary condition value used in the simulation
simulation_data /= norm_U
# Initialize the comfort class array
comfort_class = np.zeros((data_size))
# Loop over historical wind data and calculate the comfort class
for wind_index in tqdm(range(len(wind_speed)), desc="Computing comfort class"):
    #
    # Preliminary calculations
    #
    ustar = (wind_speed[wind_index]*kappa)/(np.log((zreference+z0)/z0))
    Ucomfort = (ustar/kappa)*np.log((z_comfort+z0)/z0)    
    # print(f"*** Ustar: {ustar:.2f} m/s | Ucomfort: {Ucomfort:.2f} m/s ***", end="\r", flush=True)
    # Get the wind direction
    wind_direction_index = int(np.round(wind_direction[wind_index]))%number_of_wind_directions    
    # Use the wind_direction_index data to classify the comfort
    tempdata = simulation_data[wind_direction_index,:]*Ucomfort
    # Calculate the comfort class
    comfort_class[tempdata > exceedance_value] += 1
# Calculate the comfort class
comfort_class /= len(wind_speed)
# Export comfort class Probability to disk
np.save(comfort_class_filename, comfort_class)
# Output message
print(f"*** Comfort class data saved to {comfort_class_filename}.npy ***")
print(f"*** Comfort class calculation took {time.time()-time1:.2f} seconds ***")
