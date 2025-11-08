import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")
# USER INPUT DATA
Uref = 5.0          # Reference Velocity m/s
Zref = 10.0         # Reference height m
z0 = 0.165          # Hydraulic roughness m
kappa = 0.41        # von Karman constant
H = 600.0           # Height of the domain in m
d = 0.0             # This is case specific for each of the cases
# Closure coefficients
Cmu = 0.09          # K-Epsilon closure model constant 
C1 = 1.44           # K-Epsilon closure model constant
C2 = 1.92           # K-Epsilon closure model constant
#
# INPUT DATA SETUP
#
z = np.linspace(0,H,250)
ustar = (Uref*kappa)/(np.log((Zref+z0)/z0))
print(f"Friction velocity: {ustar} m/s")
U = (ustar/kappa)*np.log((z - d + z0)/z0)
print(f"Driving Pressure Gradient (dpdx): {ustar**2/H}")
# RANS Simulation PROFILE -- Not used
# k = (ustar**2/np.sqrt(Cmu))*np.sqrt(C1*np.log((z-d+z0)/z0) + C2)
# epsilon = (ustar**3/(kappa*(z-d+z0)))*np.sqrt(C1*np.log((z-d+z0)/z0) + C2)
#
# PLOTTING
#
plt.figure(1,figsize=(10,6))
plt.semilogy(U/Uref,z/Zref,'kx',label=fr'- profile with $u_*$ = {ustar:.4f} m/s')
plt.axhline(1,color='k')
plt.axvline(1,color='k')
plt.xlabel(r'$U/U_{ref}$',fontsize=20)
plt.ylabel(r'$z/z_{ref}$',fontsize=20)
plt.grid()
plt.legend(fontsize=14,frameon=False)
plt.title(f'Velocity profile with z0={z0:.4f}',fontsize=20)
plt.show()
