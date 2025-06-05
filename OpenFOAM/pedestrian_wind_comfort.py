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
wind_step = 2
input_wind_directions = np.arange(wind_step,stop=360+wind_step,step=wind_step)        # Wind Directions Simulated numerically
comfort_class_filename = f'denhaag/comfort_class_lod2p2_theta_{wind_step}'                     # Name of the output file
# wind_dir_size = 52
# input_wind_directions = random_numbers = np.random.randint(1, 361, wind_dir_size)
z_comfort = 2.0                                                             # Height of the comfort class (m)
# Path to the weather station data
wind_datafilename = 'wind_data_pwc.txt'
sim_file_prefix = '/Volumes/Akshay2TB/macDesktop/Manuscripts/InReview/PatilGarciaSanchez2024-LoD/data/tarballs/lod2p2_denhaag/Umag_2'
# Log-Law profile parameters
zreference = 10.0                               # Reference height (m)
boundary_condition_value = 5.0                  # Boundary condition used for the simulation (m/s)
z0 = 0.5                                        # Roughness length (m)
kappa = 0.41                                    # von Karman constant
Cmu = 0.09                                      # k-Epsilon constant
exceedance_value = 5.0                          # This is according to NEN8100 - Maybe different for other cases
number_of_wind_directions = len(input_wind_directions)                  # Number of wind directions (degrees)
# DEBUG SWITCH
debug_switch = False                            # Debug Switch for testing
# Check if the input_wind_directions are equidistant
diff_input_wind_directions = np.diff(input_wind_directions)
is_fixed_interval = np.allclose(diff_input_wind_directions, diff_input_wind_directions[0])
#
# FILE CONFIGURATION
#
print("***********************************************")
print("********* Loading weather station data ********")
print("***********************************************")
print(f"--- WORKING FOR: {comfort_class_filename}")
print(f"    Number of simulations: {number_of_wind_directions}")
if(is_fixed_interval):
    print(f"    EQUIDISTANT wind directions")    
    print(f"    Start: {input_wind_directions[0]} | Stop: {input_wind_directions[-1]} | Interval: {input_wind_directions[4]-input_wind_directions[3]}")
else:
    print(f"    NON-EQUIDISTANT wind directions.....")        
# 
# Fetch the wind speed and direction
#
print("WARNING - This data structure assumes - ")
print("     First column is wind speed | Second column is wind direction")
data = np.loadtxt(wind_datafilename)
wind_speed = data[:,0]
wind_direction = data[:,1]
print(f"Historical Wind Dataframe size: {len(data)}")
print(f"Minimum speed: {np.min(wind_speed)} | Maximum speed: {np.max(wind_speed)}")
# Replace all entries corresponding to 0 with 360 since simulation uses 360 and not 0
# This is for data values that are closer to 0 but smaller than half of the step size - only valid for uniform stepping
if(is_fixed_interval):
    wind_direction[wind_direction < wind_step/2] = 360      
wind_direction[wind_direction == 0] = 360
# # Clear memory
del data
#
# Now load all the wind magnitude data
#
# Define read data function
def readdata(filename):
    with open(filename, 'rb') as f:
        f.seek(0)
        data = np.fromfile(f, dtype=np.float64)
    return data
# Read all data into a single dataframe for easy access
setup_data = True
print("*** Loading the simulation data to memory ***")
time1 = time.time()
for wind_index, iter in zip(input_wind_directions,range(0,len(input_wind_directions))):        
    # Round the input_wind_direction to the nearest available integer
    wind_index_load = int(wind_index)
    if(debug_switch):
        print(f'{sim_file_prefix}_{wind_index_load}.bin')
    tempdata = readdata(f'{sim_file_prefix}_{wind_index_load}.bin')            
    if(setup_data):       
        data_size = np.shape(tempdata)[0]        
        simulation_data = np.zeros((number_of_wind_directions,data_size))
        setup_data = False
    # Assign the data to the correct wind direction
    simulation_data[iter,:] = tempdata    
print(f"*** Simulation data loaded in {time.time()-time1:.2f} seconds ***")
# 
# Now we can calculate the comfort class
#
print("NOTICE: The comfort class calculations rounds the wind direction to the nearest integer value!")
# Get the value of the wind speed at the zcomfort height
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
    # Get the wind direction
    difference_array_wind_directions = input_wind_directions - np.round(wind_direction[wind_index])
    wind_direction_index = np.where(np.min(abs(difference_array_wind_directions)) == abs(difference_array_wind_directions))[0]      
    # Use the wind_direction_index data to classify the comfort
    tempdata = simulation_data[wind_direction_index[0],:]*Ucomfort
    # Calculate the comfort class
    comfort_class[tempdata > exceedance_value] += 1
# Calculate the comfort class
comfort_class /= len(wind_speed)
# Export comfort class Probability to disk
np.save(comfort_class_filename, comfort_class)
# Output message
print(f"*** Comfort class data saved to {comfort_class_filename}.npy ***")
print(f"*** Comfort class calculation took {time.time()-time1:.2f} seconds ***")


