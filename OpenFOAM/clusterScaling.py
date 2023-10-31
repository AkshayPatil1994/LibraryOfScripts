# Import libraries
import numpy as np
import matplotlib.pyplot as plt
#
# Define the plotting fancy plotting function
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
#
# Beging the program
#
figx, figy = 20,7                  # Size of the figure
cpu2 = np.loadtxt('cpu2.dat')       # Nprocs = 2
cpu4 = np.loadtxt('cpu4.dat')       # Nprocs = 4
cpu8 = np.loadtxt('cpu8.dat')       # Nprocs = 8
cpu16 = np.loadtxt('cpu16.dat')     # Nprocs = 16
cpu32 = np.loadtxt('cpu32.dat')     # Nprocs = 32
cpu48 = np.loadtxt('cpu48.dat')     # Nprocs = 48
cpu64 = np.loadtxt('cpu64.dat')     # Nprocs = 64
cpu96 = np.loadtxt('cpu96.dat')     # Nprocs = 96
# Compute time per dt
cpu2 = np.gradient(cpu2)
cpu4 = np.gradient(cpu4)
cpu8 = np.gradient(cpu8)
cpu16 = np.gradient(cpu16)
cpu32 = np.gradient(cpu32)
cpu48 = np.gradient(cpu48)
cpu64 = np.gradient(cpu64)
cpu96 = np.gradient(cpu96)
# Compute the mean time/dt
# Here we assume that between 1 and 2, code scales linearly!
nprocs = np.array([1,2,4,8,16,32,48,64,96])
tdt = np.array([np.mean(cpu2)*2,np.mean(cpu2),np.mean(cpu4),np.mean(cpu8),np.mean(cpu16),np.mean(cpu32),np.mean(cpu48),np.mean(cpu64),np.mean(cpu96)])
S = tdt[0]/tdt                  # Speedup
E = tdt[0]/(nprocs*tdt)         # Parallel Efficiecncy
#
# Plotting
#
fixPlot(thickness=2.0, fontsize=25, markersize=16, labelsize=20, texuse=True, tickSize = 15)
plt.figure(1,figsize=(figx,figy))
plt.subplot(1,3,1)
plt.plot(nprocs,S,'k-o',label='OpenFOAM @ Genoa')
plt.plot(nprocs,nprocs,'r:',label='Ideal')
plt.plot(nprocs[6],S[6],'rx')
plt.legend(loc='upper left',edgecolor='black',frameon=False,ncols=1)
plt.axis('square')
plt.ylabel(r'$S = t_{i=1}/t_i$',fontsize=20)
plt.xlabel(r'$p$',fontsize=20)
plt.subplot(1,3,2)
plt.plot(nprocs,E*100,'k-o')
# plt.legend(loc='upper right',edgecolor='black',frameon=False,ncols=1)
plt.ylabel(r'$E = t_{i=1}/(p t_i)$',fontsize=20)
plt.xlabel(r'$p$',fontsize=20)
plt.plot(nprocs[6],E[6]*100,'rx')
plt.subplot(1,3,3)
plt.loglog(nprocs,tdt,'k-o')
plt.loglog(nprocs[6],tdt[6],'rx')
# plt.legend(loc='upper right',edgecolor='black',frameon=False,ncols=1)
plt.axis('square')
plt.xlabel(r'$p$',fontsize=20)
plt.ylabel(r'$t/\Delta t$  $[s]$',fontsize=20)
plt.yticks([1,10,100])
# plt.show()


plt.figure(2)
fixPlot(thickness=2.0, fontsize=25, markersize=16, labelsize=20, texuse=True, tickSize = 15)
plt.plot(cpu48)
plt.xlabel('Iteration')
plt.ylabel(r'$t$ $[s]$')
plt.show()
