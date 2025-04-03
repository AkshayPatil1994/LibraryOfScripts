from vtk.util.numpy_support import vtk_to_numpy
from vtk import vtkPolyDataReader
import numpy as np
import time
import os
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
xmin, xmax = -500, 500  # Adjust as needed
ymin, ymax = -500, 1000  # Adjust as needed
# Data structure layout
simendtime ='3200'                          # Simulation end time
sa = 1                                      # Starting angle of the dataset
aint = 1                                    # Interval between consquetive angles
ea = 360                                    # Ending angle of the dataset
zloc = [2,3,5,7,10]                         # Locations where the data is available
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
for myz in zloc:
        write_coordinates = True
        for wd in wind_directions:
            time1 = time.time()
            ufile = '../allrun/results/postProcessing_'+str(wd)+'/cuttingPlane/'+simendtime+'/'+ \
                        str(vars[0])+'_cutz'+str(myz)+'.vtk'
            tkefile = '../allrun/results/postProcessing_'+str(wd)+'/cuttingPlane/'+simendtime+'/'+ \
                        str(vars[1])+'_cutz'+str(myz)+'.vtk'
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
