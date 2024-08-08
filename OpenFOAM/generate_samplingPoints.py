from functions import generate_uniform_points, load_obj, plot_mesh_and_points, fixPlot
import numpy as np
#
# User input data
#
visualisePoints=True            # Plot the points along with the geometry
printPoints=True                # Print the points to screen
savePoints2File=False           # Save the points to a file
ximin = [389,315,0.2]           # Minimum coordinate in x, y, and z
ximax = [415,858,108]           # Maximum coordinate in x, y, and z
bf = 1                          # Boundary scaling factor (bf > 1 larger domain sampling in x and y)
numberOfPoints = 200            # Number of points in total
obj_file_path = '../nominal/geo/Mesh_Buildings.obj'  # Replace with the path to your OBJ file
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
#       Do not touch beyond this line unless you are absolutely sure of what              #
#       you are doing                                                                     #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# Set up the bounding box
x_min, x_max = -bf*ximin[0], bf*ximax[0]
y_min, y_max = -bf*ximin[1], bf*ximax[1]
z_min, z_max = ximin[2], ximax[2]
# Save Points to file after generation
if(savePoints2File):
	print("Points will be saved to file")
	samplingPoints = generate_uniform_points(x_min,x_max,y_min,y_max,z_min,z_max,numberOfPoints,savePoints2File)
else:
	samplingPoints = np.loadtxt('points.csv',skiprows=1)
# Plot the points to visualise
if(visualisePoints):
    mesh = load_obj(obj_file_path)
    fixPlot(thickness=1.5, fontsize=20, markersize=8, labelsize=15, texuse=True, tickSize = 10)
    plot_mesh_and_points(mesh=mesh,points=samplingPoints)
# Print all the points to screen
if(printPoints):
	# Print to screen points
	for i in range(len(samplingPoints)):
		print("(%f %f %f)"%(samplingPoints[i,0],samplingPoints[i,1],samplingPoints[i,2]))
