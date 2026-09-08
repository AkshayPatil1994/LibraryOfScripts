# ---
# purpose: Generates Latin Hypercube samples of wind direction from historical wind data via inverse-CDF sampling.
# usage: run as script; edit n_samples/wind_datafilename inline.
# tags: prep, analysis
# note: predecessor of lhs_mda_2d_comparison.py — dup.
# ---
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from pyDOE import lhs
#
# Load and process data
#
n_samples = 6  
wind_datafilename = 'wind_data_pwc.txt'
data = np.loadtxt(wind_datafilename)
wind_speed = data[:,0]
wind_direction = data[:,1]
print(f"Historical Wind Dataframe size: {len(data)}")
#
# Histogram of wind direction
#
count, bins = np.histogram(wind_direction, bins=360, density=False)
bin_center = 0.5 * (bins[:-1] + bins[1:])
pdf = count / np.sum(count)
cdf = np.cumsum(pdf)
#
# Interpolator to do inverse CDF sampling
#
inv_cdf = interp1d(cdf, bin_center, kind='quadratic', bounds_error=True, fill_value=(bin_center[0], bin_center[-1]))
lhs_samples = lhs(1, samples=n_samples,criterion='c')  
lhs_cdf_samples = lhs_samples.flatten()
lhs_wind_directions = inv_cdf(lhs_cdf_samples)
print(','.join(map(str, np.sort(np.round(lhs_wind_directions)))))
#
# Plot for verification
#
plt.figure(1)
# plt.plot(pdf,bin_center,'r')
plt.bar(bin_center,pdf)
plt.bar(lhs_wind_directions,height=0.01)
plt.show()
