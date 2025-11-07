import numpy as np
import matplotlib.pyplot as plt
from functions import gen_grid, round_to_multiple, plot_grid, get_decomp, getN
import warnings, sys
warnings.filterwarnings("ignore",category=UserWarning)
#
# USER INPUT PARAMETERS
#
Hbuilding = 90.0                     # Height of the building
L = [3400,2500,600]                  # Length of the domain in x, y, and z (stream, span, vert)
delta = [2.5,2.5,2.5]                # Target resolution in x, y, and z (stream, span, vert)
Nprocs = 192*3                       # Number of processors used in the simulation
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
if (Nprocs != int(procx*procy)):
    sys.exit(f"{Nprocs} is not equal to {procx*procy}")

if(bl_stretch):    
    # Calculate parameters for input
    hlin = hlin_factor*Hbuilding
    Nz_lin = int(hlin/dzlin)+1
    
    # Use optimized grid point calculation
    Nx = getN(L[0], delta[0], procx)
    Ny = getN(L[1], delta[1], procy)
    Nz_tot = getN(L[2], delta[2], Nprocs)
    
    # Solve for grid parameters in z
    zh, zf, dzf, gf, il = gen_grid(L[2], Nz_tot, dzlin, hlin, max_stretch_ratio=10.0, use_geom = False, tol=1e-9)    
    
    # Print a brief summary
    print("*** SUMMARY OF PARAMETERS ***")
    print(f"Using {Nz_lin} grid points over {np.round(hlin,2)} m with a target resolution of dz:{hlin/Nz_lin} m...")
    print(f"Suggested grid -- Nx: {Nx} | Ny: {Ny} | Nz: {Nz_tot}")
    print(f"Domain size -- Lx: {L[0]} | Ly: {L[1]} | Lz: {L[2]}")
    print(f"Actual grid size -- dx: {L[0]/Nx:.5f} (target: {delta[0]}) | dy: {L[1]/Ny:.5f} (target: {delta[1]}) | dz: {L[2]/Nz_tot:.5f} (target: {delta[2]})")
    print(f"Grid stretching parameter -- stretchconst: {gf:.5f}")
    print(f"Decomposition -- procx: {procx} | procy: {procy}")
    print(f"Verification -- Nx%procx={Nx%procx} | Ny%procy={Ny%procy} | Nz%Nprocs={Nz_tot%Nprocs}")
    print("----- MEMORY REQUIREMENTS using Driver -----")
    n_field=3               # Number of fields imposed (u,v,w)
    planar_memory = Ny*Nz_tot*N_samples*n_field*8/1e9
    print(f"Additional memory per CPU: {planar_memory/Nprocs:.3f} GB | Total mem: {planar_memory:.3f} GB")
    
    # Show grid if asked
    if(show_grid):
        plot_grid(hlin,Nz_tot,dzf,zf)
else:
    # Use optimized grid point calculation
    Nx = getN(L[0], delta[0], procx)
    Ny = getN(L[1], delta[1], procy)
    
    # For Nz, find the optimal value that's divisible by procx AND procy
    # This ensures it can be decomposed properly
    N_ideal_z = L[2] / delta[2]
    
    # Find all candidates that are divisible by both procx and procy
    best_Nz = None
    best_error = float('inf')
    
    # Search range around the ideal value
    search_min = max(1, int(N_ideal_z * 0.5))
    search_max = int(N_ideal_z * 1.5) + 1
    
    for N_candidate in range(search_min, search_max):
        if N_candidate % procx == 0 and N_candidate % procy == 0:
            dz_candidate = L[2] / N_candidate
            error = abs(dz_candidate - delta[2])
            
            if error < best_error:
                best_error = error
                best_Nz = N_candidate
    
    Nz_tot = best_Nz if best_Nz is not None else round_to_multiple(N_ideal_z, Nprocs)
    
    print("*** SUMMARY OF PARAMETERS ***")
    print(f"Using constant grid over z....")
    print(f"Suggested grid -- Nx: {Nx} | Ny: {Ny} | Nz: {Nz_tot}")
    print(f"Domain size -- Lx: {L[0]} | Ly: {L[1]} | Lz: {L[2]}")
    print(f"Actual grid size -- dx: {L[0]/Nx:.5f} (target: {delta[0]}) | dy: {L[1]/Ny:.5f} (target: {delta[1]}) | dz: {L[2]/Nz_tot:.5f} (target: {delta[2]})")
    print(f"Decomposition -- procx: {procx} | procy: {procy}")
    print(f"Verification -- Nx%procx={Nx%procx} | Ny%procy={Ny%procy} | Nz%procx={Nz_tot%procx} | Nz%procy={Nz_tot%procy}")
    print("----- MEMORY REQUIREMENTS using Driver -----")
    n_field=3               # Number of fields imposed (u,v,w)
    planar_memory = Ny*Nz_tot*N_samples*n_field*8/1e9
    print(f"Additional memory per CPU: {planar_memory/Nprocs:.3f} GB | Total mem: {planar_memory:.3f} GB")
