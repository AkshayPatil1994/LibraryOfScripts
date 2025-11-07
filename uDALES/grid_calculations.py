import numpy as np
import matplotlib.pyplot as plt
from functions import gen_grid, round_to_multiple, plot_grid, get_decomp
import warnings
warnings.filterwarnings("ignore",category=UserWarning)
#
# USER INPUT PARAMETERS
#
Hbuilding = 90.0                     # Height of the building
L = [3400,2500,600]                  # Length of the domain in x, y, and z (stream, span, vert)
delta = [2.65,2.65,2.34]             # Target resolution in x, y, and z (stream, span, vert)
Nprocs = 512                        # Number of processors used in the simulation
# Secondary parameters
N_samples = 10000                   # Number of input planes used in the precursor
bl_stretch = False                  # Is the grid stretched in vertical?
hlin_factor = 1.11                  # hlin = hlin_factor*Hbuilding (typically 10% i.e., 1.1)
Nz_tot = 256                        # Total number of grid points over the vertical direction
dzlin = 2.0                         # Target grid resolution over Hbuilding*hlin_factor
show_grid = False                   # Plot the grid 
#
# MAIN
#
Nprocs = int(Nprocs)
procx, procy = get_decomp(Nprocs)
if(bl_stretch):    
    # Calcuate parameters for input
    hlin = hlin_factor*Hbuilding
    Nz_lin = int(hlin/dzlin)+1
    Nx_temp = L[0]/delta[0]
    Ny_temp = L[1]/delta[1]
    Nx = round_to_multiple(Nx_temp,Nprocs)
    Ny = round_to_multiple(Ny_temp,Nprocs)
    Nz_tot = round_to_multiple(Nz_tot,Nprocs)
    # Solve for grid parameters in z
    zh, zf, dzf, gf, il = gen_grid(L[2], Nz_tot, dzlin, hlin, max_stretch_ratio=10.0, use_geom = False, tol=1e-9)    
    # Print a brief summary
    print("*** SUMMARY OF PARAMETERS ***")
    print(f"Using {Nz_lin} grid points over {np.round(hlin,2)} m with a target resolution of dz:{hlin/Nz_lin} m...")
    print(f"Suggested grid -- Nx: {Nx} | Ny: {Ny} | Nz: {Nz_tot}")
    print(f"Domain size -- Lx: {L[0]} | Ly: {L[1]} | Lz: {L[2]}")
    print(f"Grid stretching parameter -- stretchconst: {gf:.5f}")
    print(f"Decomposition -- procx: {procx} | procy: {procy}")
    print("----- MEMORY REQUIREMENTS using Driver -----")
    n_field=3               # Number of fields imposed (u,v,w)
    planar_memory = Ny*Nz_tot*N_samples*n_field*8/1e9
    print(f"Additional memory per CPU: {planar_memory/Nprocs} GB | Total mem: {planar_memory} GB")
    # Show grid if asked
    if(show_grid):
        plot_grid(hlin,Nz_tot,dzf,zf)
else:
    Nx_temp = L[0]/delta[0]
    Ny_temp = L[1]/delta[1]
    Nz_temp = L[2]/delta[2]
    Nx = round_to_multiple(Nx_temp,Nprocs)
    Ny = round_to_multiple(Ny_temp,Nprocs)
    Nz_tot = int(Nz_temp)
    if (Nz_tot < Nprocs):
        Nz_tot = Nz_tot
    else:
        Nz_tot = round_to_multiple(Nz_tot,Nprocs)
    print("*** SUMMARY OF PARAMETERS ***")
    print(f"Using constant grid over z....")
    print(f"Suggested grid -- Nx: {Nx} | Ny: {Ny} | Nz: {Nz_tot}")
    print(f"Domain size -- Lx: {L[0]} | Ly: {L[1]} | Lz: {L[2]}")
    print(f"Grid size -- dx: {L[0]/Nx:.3} | dy: {L[1]/Ny:.3} | dz: {L[2]/Nz_tot:.3}")   
    print(f"Decomposition -- procx: {procx} | procy: {procy}") 
    print("----- MEMORY REQUIREMENTS using Driver -----")
    n_field=3               # Number of fields imposed (u,v,w)
    planar_memory = Ny*Nz_tot*N_samples*n_field*8/1e9
    print(f"Additional memory per CPU: {planar_memory/Nprocs} GB | Total mem: {planar_memory} GB")
