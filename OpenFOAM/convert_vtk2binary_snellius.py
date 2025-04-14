from vtk.util.numpy_support import vtk_to_numpy
from vtk import vtkPolyDataReader
import numpy as np
import time
import os
import sys
#
# Binary File convert function
#
def save_to_binary(filename, array,my_datatype=np.float64):
    with open(filename, 'wb') as f:
        array.astype(my_datatype).tofile(f)
    f.close()
#
# User input data
#
# User-defined bounding box
xmin, xmax = -1400, 1400  # Adjust as needed
ymin, ymax = -1400, 1400  # Adjust as needed
# Data structure layout
simendtime ='1200'                          # Simulation end time
sa = 1                                      # Starting angle of the dataset
aint = 1                                    # Interval between consquetive angles
ea = 360                                    # Ending angle of the dataset
zloc = [2,5,10,50,100]                      # Locations where the data is available
vars = ['U','k']                            # Variables to average
#
# Loop over all u and k files to convert
#
# Assert output directory exists, if not create it
if not os.path.exists('data'):
    os.makedirs('data')
# Generate the VTK reader, only done once at the start
reader = vtkPolyDataReader()
readertke = vtkPolyDataReader()
# Setup the angles
wind_directions = np.arange(start=sa,step=aint,stop=ea+aint)
# First check all data is available
for myz in zloc:
	for wd in wind_directions:
		# Name of the files zcut_5_U.vtk
		print(f"Checking files for theta = {wd}")
		ufile = '../'+str(wd)+'/postProcessing/sampling_planes/'+simendtime+'/'+ \
                        'zcut_'+str(myz)+'_'+str(vars[0])+'.vtk'
		tkefile = '../'+str(wd)+'/postProcessing/sampling_planes/'+simendtime+'/'+ \
                        'zcut_'+str(myz)+'_'+str(vars[1])+'.vtk'
		if (not (os.path.isfile(ufile) and os.path.isfile(tkefile))):
			print(f"{ufile}")
			print(f"{tkefile}")
			print("Above files are missing....")
			sys.exit()
# Print file exists tag
print("All files for conversion present")
print("Starting VTK 2 Binary conversion....")
# If exit does not happen then carry out the analysis
for myz in zloc:
        write_coordinates = True
        for wd in wind_directions:
            time1 = time.time()
            ufile = '../'+str(wd)+'/postProcessing/sampling_planes/'+simendtime+'/'+ \
                        'zcut_'+str(myz)+'_'+str(vars[0])+'.vtk'
            tkefile = '../'+str(wd)+'/postProcessing/sampling_planes/'+simendtime+'/'+ \
                        'zcut_'+str(myz)+'_'+str(vars[1])+'.vtk'
            # Read the data
            reader.SetFileName(ufile)
            readertke.SetFileName(tkefile)
            reader.Update()
            readertke.Update()
            # Extract the data from the reader
            pudata = reader.GetOutput()
            ptkedata = readertke.GetOutput()            
            # Write the coordinates only once for each height and get the mask only once at the start
            if(write_coordinates):
                # Read the coordinates from the VTK reader
                coordinates = vtk_to_numpy(pudata.GetPoints().GetData())
                mask = (coordinates[:, 0] >= xmin) & (coordinates[:, 0] <= xmax) & \
                    (coordinates[:, 1] >= ymin) & (coordinates[:, 1] <= ymax)
                # Slice the x and y to the bounding box
                filter_x = coordinates[mask,0]
                filter_y = coordinates[mask,1]
                # Write the coordinates to file for this height
                x_filename = 'data/x_'+str(myz)+'.bin'
                y_filename = 'data/y_'+str(myz)+'.bin'
                save_to_binary(x_filename,filter_x)
                save_to_binary(y_filename,filter_y)
                # Set the write coordinates flag to false for this height
                write_coordinates = False
            # Continue writing data for tke and mag(U)
            Udata = vtk_to_numpy(pudata.GetPointData().GetArray(0))
            tke = vtk_to_numpy(ptkedata.GetPointData().GetArray(0))
            filter_speed = np.sqrt(Udata[mask,0]**2+Udata[mask,1]**2+Udata[mask,2]**2)
            filter_tke = tke[mask]
            # Write to file
            speed_filename = 'data/Umag_'+str(myz)+'_'+str(wd)+'.bin'
            tke_filename = 'data/TKE_'+str(myz)+'_'+str(wd)+'.bin'
            save_to_binary(speed_filename,filter_speed)
            save_to_binary(tke_filename,filter_tke)
            print(f"Case - Height: {myz} | theta: {wd} finished in {time.time() - time1} seconds")
