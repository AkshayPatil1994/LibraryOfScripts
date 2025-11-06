import numpy as np
import matplotlib.pyplot as plt

filename = 'lscale.inp.003'

data = np.loadtxt(filename,skiprows=2)

dz = np.gradient(data[:,0])


plt.figure(1,figsize=(10,8))
plt.title('Grid points',fontsize=25)
plt.semilogy(dz,data[:,0],'kx')
plt.xlabel(r'$\Delta x_3$',fontsize=20)
plt.ylabel(r'$x_3$',fontsize=20)
plt.grid()
plt.show()
