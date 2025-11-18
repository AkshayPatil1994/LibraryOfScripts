import numpy as np
import matplotlib.pyplot as plt
#
# LOAD THE DAT
#
fluid_boundary = np.loadtxt('fluid_boundary_c.txt',skiprows=1)
#
# PLOT
#
plt.figure(1)
plt.scatter(fluid_boundary[:,0],fluid_boundary[:,1],c=fluid_boundary[:,2],cmap='magma',s=2)
plt.colorbar()
plt.savefig('boundarypoints.png',dpi=300)
plt.show()
