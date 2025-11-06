import numpy as np

dtmax = 0.18    # Maximum time step allowed in s
Tsim = 600      # Simulation time in s
H = 95.0        # Height of the building in m
Lb = 1000.0     # Length of the built area in m (streamwise direction)
Uref = 5.0      # Reference velocity in m/s
Zref = 10.0     # Reference height in m
z0 = 0.5        # Aerodynamic roughness in m
eddy_factor = 15    # Number of eddy turn overs before sampling begins
#
# Define some constants
#
kappa = 0.41        # von Karman constant
Hdomain = 6*H       # Height of the simulation domain based on best practice guidelines
# Build the log-law 
u_star = (Uref*kappa)/(np.log((Zref+z0)/z0))
print(f"Friction velocity: {u_star} m/s")
print(f"Height of the simulation domain: {6*H} m")
print(f"Driving pressure gradient dpdx: {u_star**2/Hdomain}")
T_eddy = Hdomain/u_star
print(f"Eddy turn over time: {T_eddy} s")
T_conv = (20*H + Lb)/Uref
print(f"Convective time scale: {T_conv} s")
print("---------")
print(f"Precursor simulation for 15 eddy turns: {15*T_eddy} s")
print(f"Sample the precursor for driven simulation for: {2*T_conv + Tsim} s")
print("---------")
print(f" *** Total precursor simulation time: {15*T_eddy + 2*T_conv + Tsim} s")
print(f" *** Precursor spinup time: {15*T_eddy} s")
print(f" *** driverstore: {int((2*T_conv + Tsim)/dtmax) + 1}")
