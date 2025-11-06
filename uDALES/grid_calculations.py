import numpy as np
import matplotlib.pyplot as plt
from functions import gen_grid, round_to_multiple, plot_grid
import warnings
warnings.filterwarnings("ignore",category=UserWarning)
#
# USER INPUT PARAMETERS
#
Hbuilding = 90.0                    # Height of the building
L = [3400,2500,600]                 # Length of the domain in x, y, and z (stream, span, vert)
delta = [2.0,2.0,1.0]               # Target resolution in x, y, and z (stream, span, vert)
Nprocs = 192                        # Number of processors used in the simulation
# Secondary parameters
bl_stretch = True                   # Is the grid stretched in vertical?
hlin_factor = 1.11                  # hlin = hlin_factor*Hbuilding (typically 10% i.e., 1.1)
Nz_tot = 256                        # Total number of grid points over the vertical direction
dzlin = 1.0                         # Target grid resolution over Hbuilding*hlin_factor
show_grid = True                    # Plot the grid 
#
# MAIN
#
if(bl_stretch):    
    # Calcuate parameters for input
    hlin = hlin_factor*Hbuilding
    Nz_lin = int(hlin/dzlin)+1
    Nx_temp = L[0]/delta[0]
    Ny_temp = L[1]/delta[1]
    Nx = round_to_multiple(Nx_temp,Nprocs)
    Ny = round_to_multiple(Ny_temp,Nprocs)
    # Solve for grid parameters in z
    zh, zf, dzf, gf, il = gen_grid(L[2], Nz_tot, dzlin, hlin, max_stretch_ratio=10.0, use_geom = False, tol=1e-9)
    # Print a brief summary
    print("*** SUMMARY OF PARAMETERS ***")
    print(f"Using {Nz_lin} grid points over {np.round(hlin,2)} m with a target resolution of dz:{hlin/Nz_lin} m...")
    print(f"Suggested grid -- Nx: {Nx} | Ny: {Ny} | Nz: {Nz_tot}")
    print(f"Grid stretching parameter -- stretchconst: {gf:.5f}")
    # Show grid if asked
    if(show_grid):
        plot_grid(hlin,Nz_tot,dzf,zf)
