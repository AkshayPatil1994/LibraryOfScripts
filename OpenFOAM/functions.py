import numpy as np
import random
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.mplot3d import Axes3D
import trimesh
import sys
#
# Function that outputs the sampled points
#
def generate_uniform_points(x_min, x_max, y_min, y_max, z_min, z_max, num_points,savePoints2File=False):
    '''
    Generate uniformly distributed points within specified limits for x, y, and z coordinates.
    
    Args:
    x_min (float): Minimum limit for x coordinate.
    x_max (float): Maximum limit for x coordinate.
    y_min (float): Minimum limit for y coordinate.
    y_max (float): Maximum limit for y coordinate.
    z_min (float): Minimum limit for z coordinate.
    z_max (float): Maximum limit for z coordinate.
    num_points (int): Number of points to generate.
    savePoints2File (Boolean): Save points to a text file
    
    Returns:
    list: List of generated points as tuples (x, y, z).
    '''
    points = []
    for _ in range(num_points):
        x = random.uniform(x_min, x_max)
        y = random.uniform(y_min, y_max)
        z = random.uniform(z_min, z_max)
        # Force round to 4 places
        x = round(x,4)
        y = round(y,4)
        z = round(z,4)
        points.append((x, y, z))
    
    # Write the points to file
    if(savePoints2File):
        np.savetxt('points.csv',np.array(points),header='X Y Z',comments='')

    return points
#
# Plot the points function
#
def plot_only_points(points,figx=14,figy=8):
    '''
    Plot the given points in a 3D plot.
    
    Args:
    points (list): List of tuples containing 3D coordinates (x, y, z).
    '''

    fig = plt.figure(figsize=(figx,figy))
    ax = fig.add_subplot(111, projection='3d')
    
    x_coords, y_coords, z_coords = zip(*points)
    ax.scatter(x_coords, y_coords, z_coords, c='b', marker='o')
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    
    plt.show()
#
# Load the obj file
#
def load_obj(file_path):
    '''
        This function loads the mesh and returns the mesh object using trimesh
    '''
    return trimesh.load(file_path,force='mesh')
#
# Plot the mesh and the points together
#
def plot_mesh_and_points(mesh, points,figx=14,figy=8, saveMyFigure=False):
    '''
        This function plots the mesh as a surface and points generated and returns the figure
    '''

    fig = plt.figure(figsize=(figx, figy))
    ax = fig.add_subplot(projection='3d')
    
    # Plot the mesh
    vertices = mesh.vertices
    faces = mesh.faces
    x_coords, y_coords, z_coords = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    ax.plot_trisurf(x_coords, y_coords, faces, z_coords, linewidth=0.2, edgecolor='black', alpha=0.8)
    
    # Plot the generated points
    x_coords, y_coords, z_coords = zip(*points)
    ax.scatter(x_coords, y_coords, z_coords, c='r', marker='o', label=r'Sampling Points')
    
    ax.set_xlabel(r'$x_1$',labelpad=15, fontsize=20)
    ax.set_ylabel(r'$x_2$',labelpad=15, fontsize=20)
    ax.set_zlabel(r'$x_3$',labelpad=15, fontsize=20)
    ax.legend()
    ax.axis('square')
    ax.set_xlim([np.min(x_coords),np.max(x_coords)])
    ax.set_ylim([np.min(y_coords),np.max(y_coords)])
    ax.set_zlim([0,1.5*np.max(z_coords)])

    # Automatically set ticks without cluttering the axes
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.zaxis.set_major_locator(MaxNLocator(integer=True))
    # Save figure if user prompts
    if(saveMyFigure):
        plt.savefig('samplingPoints.png',dpi=500)
    plt.show()
#
# Function to read the probes
#
def readFoamProbes(filename,numProbes=10,fieldName='scalar'):
    '''
        This function reads the OpenFOAM generated probes as numpy arrays
    INPUT
        filename:   [string] Name and location of the file containing the data
        numProbes:  [integer] Number of points sampled in the domain
        fieldname:  [string] Scalar or vector quantity to be read
    OUTPUT
        dataout:    [numpy array] Returns a numpy array for the `fieldName`
    '''
    # Commented to make it compatible with older python versions as match case does not work with older python
    # match fieldName:
    #     case 'scalar':
    #         dataout = np.loadtxt(filename,skiprows=numProbes+2)            
    #     case 'vector':
    #         #dataout = np.loadtxt(filename,skiprows=numProbes+2)
    #         with open(filename,'r') as file:
    #             lines = file.readlines()[numProbes+2:]
    #         procLines = [line.replace('(', '').replace(')', '').split() for line in lines]
    #         dataout = np.array(procLines,dtype=float)
    #     case _:
    #         sys.exit("\033[1;31;47mError: Unknown field type `%s` | Valid field type: scalar or vector...\033[0m"%(fieldName))
    if fieldName == 'scalar':
        dataout = np.loadtxt(filename, skiprows=numProbes+2)
    elif fieldName == 'vector':
        with open(filename, 'r') as file:
            lines = file.readlines()[numProbes+2:]
            procLines = [line.replace('(', '').replace(')', '').split() for line in lines]
            dataout = np.array(procLines, dtype=float)
    else:
        import sys
        sys.exit("\033[1;31;47mError: Unknown field type `%s` | Valid field type: scalar or vector...\033[0m" % (fieldName))


    return dataout
#
# Read an obj
#
def load_obj1(file_path):
    vertices = []
    faces = []

    with open(file_path, 'r') as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue

            if parts[0] == 'v':
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif parts[0] == 'f':
                face = [int(x.split('/')[0]) - 1 for x in parts[1:]]
                faces.append(face)

    return np.array(vertices), np.array(faces)
#
# Set default plotting size
#
def fixPlot(thickness=1.5, fontsize=20, markersize=8, labelsize=15, texuse=False, tickSize = 15):
    '''
        This plot sets the default plot parameters
    INPUT
        thickness:      [float] Default thickness of the axes lines
        fontsize:       [integer] Default fontsize of the axes labels
        markersize:     [integer] Default markersize
        labelsize:      [integer] Default label size
    OUTPUT
        None
    '''
    # Set the thickness of plot axes
    plt.rcParams['axes.linewidth'] = thickness    
    # Set the default fontsize
    plt.rcParams['font.size'] = fontsize    
    # Set the default markersize
    plt.rcParams['lines.markersize'] = markersize    
    # Set the axes label size
    plt.rcParams['axes.labelsize'] = labelsize
    # Enable LaTeX rendering
    plt.rcParams['text.usetex'] = texuse
    # Tick size
    plt.rcParams['xtick.major.size'] = tickSize
    plt.rcParams['ytick.major.size'] = tickSize
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
